import json

from django.core.files.uploadedfile import UploadedFile
from django.http import StreamingHttpResponse, Http404, QueryDict
from rest_framework.response import Response

from .serializers import RelatedFileSerializer



def _delete_related_file(parent, field):
    """ Delete an attached RelatedFile model 
        without triggering a cascade delete
    """
    if getattr(parent, field) is not None:
        current = getattr(parent, field, None)
        setattr(parent, field, None)
        parent.save(update_fields=[field])
        current.delete()

def _get_chunked_content(f, chunk_size=1024):
    content = f.read(chunk_size)
    while content:
        yield content
        content = f.read(chunk_size)


def _handle_get_related_file(parent, field):
    f = getattr(parent, field)

    if not f:
        raise Http404()

    response = StreamingHttpResponse(_get_chunked_content(f.file), content_type=f.content_type)
    if f.filename:
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(f.filename)
    else:
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(f.file.name)
    return response


def _handle_post_related_file(parent, field, request, content_types):
    serializer = RelatedFileSerializer(data=request.data, content_types=content_types, context={'request': request})
    serializer.is_valid(raise_exception=True)
    instance = serializer.create(serializer.validated_data)

    # Check for exisiting file and delete
    _delete_related_file(parent, field)

    setattr(parent, field, instance)
    parent.save(update_fields=[field])

    # Override 'file' return to hide storage details with stored filename
    response = Response(RelatedFileSerializer(instance=instance, content_types=content_types).data)
    response.data['file'] = instance.file.name
    return response


def _handle_delete_related_file(parent, field):
    if not getattr(parent, field, None):
        raise Http404()

    _delete_related_file(parent, field)
    return Response()


def _json_write_to_file(parent, field, request, serializer):
    json_serializer = serializer()
    data = json_serializer.validate(request.data)

    # create file object
    with open(json_serializer.filenmame, 'wb+') as f:
        in_memory_file = UploadedFile(
            file=f,
            name=json_serializer.filenmame,
            content_type='application/json',
            size=len(data.encode('utf-8')),
            charset=None
        )

    # wrap and re-open file
    file_obj = QueryDict('', mutable=True)
    file_obj.update({'file': in_memory_file})
    file_obj['file'].open()
    file_obj['file'].seek(0)
    file_obj['file'].write(data.encode('utf-8'))
    serializer = RelatedFileSerializer(
        data=file_obj,
        content_types='application/json',
        context={'request': request}
    )

    serializer.is_valid(raise_exception=True)
    instance = serializer.create(serializer.validated_data)

    # Check for exisiting file and delete
    _delete_related_file(parent, field)

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

def handle_related_file(parent, field, request, content_types):
    method = request.method.lower()

    if method == 'get':
        return _handle_get_related_file(parent, field)
    elif method == 'post':
        return _handle_post_related_file(parent, field, request, content_types)
    elif method == 'delete':
        return _handle_delete_related_file(parent, field)


def handle_json_data(parent, field, request, serializer):
    method = request.method.lower()

    if method == 'get':
        return _json_read_from_file(parent, field)
    elif method == 'post':
        return _json_write_to_file(parent, field, request, serializer)
    elif method == 'delete':
        return _handle_delete_related_file(parent, field)
