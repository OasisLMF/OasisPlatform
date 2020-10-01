import os
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel


def random_file_name(instance, filename):
    if instance.store_as_filename:
        return filename

    # Work around: S3 objects pushed as '<hash>.gz' should be '<hash>.tar.gz'
    if filename.endswith('.tar.gz'):
        ext = '.tar.gz'
    else:
        ext = os.path.splitext(filename)[-1]
    return '{}{}'.format(uuid4().hex, ext)


class RelatedFile(TimeStampedModel):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    file = models.FileField(help_text=_('The file to store'), upload_to=random_file_name)
    filename = models.CharField(max_length=255, editable=False, default="", blank=True)
    # filehash_md5 = models.CharField(max_length=255, editable=False, default="", blank=True)
    content_type = models.CharField(max_length=255)
    store_as_filename = models.BooleanField(default=False)
    aws_location = models.CharField(max_length=255, editable=False, default=settings.AWS_LOCATION, blank=True)

    def __str__(self):
        return 'File_{}'.format(self.file)

    def read(self, *args, **kwargs):
        return self.file.read(*args, **kwargs)
