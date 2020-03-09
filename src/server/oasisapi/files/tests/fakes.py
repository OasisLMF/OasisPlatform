import six
from django.core.files import File
from io import BytesIO
from model_mommy import mommy

from ..models import RelatedFile


def fake_related_file(**kwargs):
    if 'file' not in kwargs:
        kwargs['file'] = File(BytesIO(b'content'), 'filename')

    if isinstance(kwargs['file'], six.binary_type):
        kwargs['file'] = File(BytesIO(kwargs['file']), 'filename')
    elif isinstance(kwargs['file'], six.string_types):
        kwargs['file'] = File(BytesIO(kwargs['file'].encode()), 'filename')

    return mommy.make(RelatedFile, **kwargs)
