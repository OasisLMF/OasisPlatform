import json
import io
import os
from tempfile import TemporaryFile

import pandas as pd
import pyarrow.parquet as pq
from django.core.files import File
from django.http import StreamingHttpResponse, Http404
from rest_framework.response import Response

from ..models import RelatedFile
from .serializers import RelatedFileSerializer, EXPOSURE_ARGS
from ...permissions.group_auth import verify_user_is_in_obj_groups, resolve_user

from ods_tools.oed.exposure import OedExposure

PARQUET_TO_CSV_BATCH_ROWS = 65536


def _delete_related_file(parent, field, user):
    """ Delete an attached RelatedFile model
        without triggering a cascade delete
    """
    if getattr(parent, field) is not None:
        current = getattr(parent, field, None)

        verify_user_is_in_obj_groups(user, current, 'You do not have permission to delete this file')

        setattr(parent, field, None)
        parent.save(update_fields=[field])
        current.delete()


def _get_chunked_content(f, chunk_size=1024):
    content = f.read(chunk_size)
    while content:
        yield content
        content = f.read(chunk_size)


def _iter_parquet_as_csv(file_obj):
    """ Yield a parquet file as csv one row batch at a time, so a large file
        (e.g. keys-errors) is never fully loaded into memory.
    """
    parquet_file = pq.ParquetFile(file_obj)
    header = True
    for batch in parquet_file.iter_batches(batch_size=PARQUET_TO_CSV_BATCH_ROWS):
        # integer_object_nulls: keep ints with nulls as ints, so a column is
        # formatted the same way in every batch.
        df = batch.to_pandas(integer_object_nulls=True)
        yield df.to_csv(index=False, header=header).encode('utf-8')
        header = False
    if header:
        # zero-row file: still return the header
        yield pd.DataFrame(columns=parquet_file.schema_arrow.names).to_csv(index=False).encode('utf-8')


def convert_tabular_file(content_type, file_obj, download_name, file_format):
    """ Return a response with a csv file as parquet or a parquet file as csv,
        or None when no conversion is needed.
    """
    if file_format == 'parquet' and content_type == 'text/csv':
        output_buffer = io.BytesIO()
        pd.read_csv(file_obj).to_parquet(output_buffer, index=False)
        output_buffer.seek(0)
        content, ext, out_content_type = output_buffer, '.parquet', 'application/octet-stream'
    elif file_format == 'csv' and content_type == 'application/octet-stream':
        content, ext, out_content_type = _iter_parquet_as_csv(file_obj), '.csv', 'text/csv'
    else:
        return None

    name, current_ext = os.path.splitext(os.path.basename(download_name))
    if current_ext not in ('.csv', '.parquet'):
        name += current_ext
    response = StreamingHttpResponse(content, content_type=out_content_type)
    response['Content-Disposition'] = 'attachment; filename="{}{}"'.format(name, ext)
    return response


def _handle_get_related_file(parent, field, request, default_file_format=None):

    # fetch file
    f = getattr(parent, field)
    if not f:
        raise Http404()

    verify_user_is_in_obj_groups(request.user, f, 'You do not have permission to read this file')
    file_format = request.GET.get('file_format', default_file_format)

    if 'converted' in request.GET:
        if not (f.converted_file and f.conversion_state == RelatedFile.ConversionState.DONE):
            raise Http404()

        download_name = f.converted_filename if f.converted_filename else f.converted_file.name
        file_obj = f.converted_file
    else:
        download_name = f.filename if f.filename else f.file.name
        file_obj = f.file

    # Non OED files (e.g. analysis lookup files) are converted without OED validation
    if field not in EXPOSURE_ARGS:
        response = convert_tabular_file(f.content_type, file_obj, download_name, file_format)
        if response:
            return response

    # Parquet format requested and data stored as csv
    if file_format == 'parquet' and f.content_type == 'text/csv':
        exposure = OedExposure(**{
            EXPOSURE_ARGS[field]: file_obj,
        })
        output_buffer = io.BytesIO()
        exposure_data = getattr(exposure, EXPOSURE_ARGS[field])
        exposure_data.dataframe.to_parquet(output_buffer, index=False)
        output_buffer.seek(0)

        response = StreamingHttpResponse(output_buffer, content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment; filename="{}{}"'.format(download_name, '.parquet')
        return response

    # CSV format requested and data stored as Parquet
    if file_format == 'csv' and f.content_type == 'application/octet-stream':
        exposure = OedExposure(**{
            EXPOSURE_ARGS[field]: file_obj,
        })
        output_buffer = io.BytesIO()
        exposure_data = getattr(exposure, EXPOSURE_ARGS[field])
        exposure_data.dataframe.to_csv(output_buffer, index=False)
        output_buffer.seek(0)

        response = StreamingHttpResponse(output_buffer, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}{}"'.format(download_name, '.csv')
        return response

    # Original Fallback method - Reutrn data 'as is'
    response = StreamingHttpResponse(_get_chunked_content(file_obj), content_type=f.content_type)
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(download_name)
    return response


def _handle_post_related_file(parent, field, request, content_types, parquet_storage, serializer_class=RelatedFileSerializer):
    serializer = serializer_class(data=request.data, content_types=content_types, context={
                                  'request': request}, parquet_storage=parquet_storage, field=field)
    serializer.is_valid(raise_exception=True)
    instance = serializer.create(serializer.validated_data)

    if hasattr(parent, 'groups'):
        instance.groups.set(parent.groups.all())
        instance.save()

    # Check for exisiting file and delete
    _delete_related_file(parent, field, request.user)

    setattr(parent, field, instance)
    parent.save(update_fields=[field])

    # Override 'file' return to hide storage details with stored filename
    response = Response(serializer_class(instance=instance, content_types=content_types).data)
    response.data['file'] = instance.file.name
    return response


def _handle_delete_related_file(parent, field, request):
    if not getattr(parent, field, None):
        raise Http404()

    _delete_related_file(parent, field, request.user)
    return Response()


def _json_write_to_file(parent, field, request, serializer):
    json_serializer = serializer()
    data = json_serializer.validate(request.data)

    # create file object
    with TemporaryFile() as tmp_file:
        tmp_file.write(data.encode('utf-8'))
        tmp_file.seek(0)

        instance = RelatedFile.objects.create(
            file=File(tmp_file, name=json_serializer.filename),
            filename=json_serializer.filename,
            content_type='application/json',
            creator=resolve_user(request.user),
        )

    # Check for exisiting file and delete
    _delete_related_file(parent, field, request.user)

    setattr(parent, field, instance)
    parent.save(update_fields=[field])

    # Override 'file' return to hide storage details with stored filename
    response = Response(RelatedFileSerializer(instance=instance, content_types='application/json').data)
    response.data['file'] = instance.file.name
    return response


def _json_read_from_file(parent, field):
    f = getattr(parent, field)
    if not f:
        raise Http404()
    else:
        return Response(json.load(f))


def handle_related_file(parent, field, request, content_types, parquet_storage=False, serializer_class=RelatedFileSerializer,
                        default_file_format=None):
    method = request.method.lower()

    if method == 'get':
        return _handle_get_related_file(parent, field, request, default_file_format)
    elif method == 'post':
        return _handle_post_related_file(parent, field, request, content_types, parquet_storage, serializer_class)
    elif method == 'delete':
        return _handle_delete_related_file(parent, field, request)


def handle_json_data(parent, field, request, serializer):
    method = request.method.lower()

    if method == 'get':
        return _json_read_from_file(parent, field)
    elif method == 'post':
        return _json_write_to_file(parent, field, request, serializer)
    elif method == 'delete':
        return _handle_delete_related_file(parent, field, request)
