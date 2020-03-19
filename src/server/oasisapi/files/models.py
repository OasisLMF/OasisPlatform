import os
from io import BytesIO
from uuid import uuid4

from django.conf import settings
from django.core.files import File
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel


def random_file_name(instance, filename):
    ext = os.path.splitext(filename)[-1]
    return '{}{}'.format(uuid4().hex, ext)


class RelatedFileManager(models.Manager):
    def create_from_content(self, content, filename, content_type, creator):
        self.create(
            creator=creator,
            filename=filename,
            content_type=content_type,
            file=File(BytesIO(content))
        )


class RelatedFile(TimeStampedModel):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    file = models.FileField(help_text=_('The file to store'), upload_to=random_file_name)
    filename = models.CharField(max_length=255, editable=False, default="", blank=True)
    # filehash_md5 = models.CharField(max_length=255, editable=False, default="", blank=True)
    content_type = models.CharField(max_length=255)

    objects = RelatedFileManager()

    def __str__(self):
        return 'File_{}'.format(self.file)

    def read(self, *args, **kwargs):
        return self.file.read(*args, **kwargs)

    def get_storage_reference(self):
        if not self.file:
            return None

        if settings.DEFAULT_FILE_STORAGE == 'storages.backends.s3boto3.S3Boto3Storage':
            return self.file.storage.url(self.file.name)
        else:
            return self.file.name
