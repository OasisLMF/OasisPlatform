import json
import io
from tempfile import TemporaryFile

from django.conf import settings
from django.core.files import File
from django.http import StreamingHttpResponse, Http404, JsonResponse
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from oasis_data_manager.df_reader.config import get_df_reader
from oasis_data_manager.df_reader.exceptions import InvalidSQLException
from ..models import RelatedFile, list_tar_file
from .serializers import RelatedFileSerializer, EXPOSURE_ARGS
from ...permissions.group_auth import verify_user_is_in_obj_groups

from ods_tools.oed.exposure import OedExposure


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


def _handle_get_related_file(parent, field, request):

    # fetch file
    f = getattr(parent, field)
    if not f:
        raise Http404()


    verify_user_is_in_obj_groups(request.user, f, 'You do not have permission to read this file')
    file_format = request.GET.get('file_format', None)

    list_files = request.query_params.get('file_mode', False)

    if 'converted' in request.GET:
        if not (f.converted_file and f.conversion_state == RelatedFile.ConversionState.DONE):
            raise Http404()

        download_name = f.converted_filename if f.converted_filename else f.converted_file.name
        file_obj = f.converted_file
    else:
        download_name = f.filename if f.filename else f.file.name
        file_obj = f.file

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

    if list_files: 
        files = list_tar_file(f)

        # todo: change this to a proper response
        return Response(files)

    # Original Fallback method - Reutrn data 'as is'
    response = StreamingHttpResponse(_get_chunked_content(file_obj), content_type=f.content_type)
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(download_name)
    return response


def _handle_post_related_file(parent, field, request, content_types, parquet_storage, oed_validate):
    serializer = RelatedFileSerializer(data=request.data, content_types=content_types, context={
                                       'request': request}, parquet_storage=parquet_storage, field=field, oed_validate=oed_validate)
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
    response = Response(RelatedFileSerializer(instance=instance, content_types=content_types).data)
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
            creator=request.user,
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


def handle_related_file(parent, field, request, content_types, parquet_storage=False, oed_validate=None):
    method = request.method.lower()

    if method == 'get':
        return _handle_get_related_file(parent, field, request)
    elif method == 'post':
        return _handle_post_related_file(parent, field, request, content_types, parquet_storage, oed_validate)
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


def handle_related_file_sql(parent, field, request, sql, m2m_file_pk=None):
    requested_format = request.GET.get('file_format', None)
    f = getattr(parent, field)

    if m2m_file_pk:
        try:
            f = f.get(pk=m2m_file_pk)
        except RelatedFile.DoesNotExist:
            raise Http404

    download_name = f.filename if f.filename else f.file.name

    reader = get_df_reader({'filepath': f.file.path, 'engine': settings.DEFAULT_READER_ENGINE})

    try:
        df = reader.sql(sql).as_pandas()
    except InvalidSQLException:
        raise ValidationError('Invalid SQL provided.')

    output_buffer = io.BytesIO()

    if requested_format == 'parquet':
        df.to_parquet(output_buffer, index=False)
        content_type = 'application/octet-stream'
    elif requested_format == 'json':
        df.to_json(output_buffer, orient='table', index=False)
        content_type = 'application/json'
    else:
        df.to_csv(output_buffer, index=False)
        content_type = 'text/csv'

    output_buffer.seek(0)
    response = StreamingHttpResponse(output_buffer, content_type=content_type)
    response['Content-Disposition'] = 'attachment; filename="{}{}"'.format(download_name, f'.{requested_format}')

    return response
