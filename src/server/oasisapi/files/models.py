import os
import json
from io import BytesIO
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.files import File
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


class RelatedFileManager(models.Manager):
    def create_from_content(self, content, filename, content_type, creator):
        self.create(
            creator=creator,
            filename=filename,
            content_type=content_type,
            file=File(BytesIO(content))
        )


def file_storage_link(storage_obj, fullpath=False):
    """
    Return link to file storage based on 'STORAGE_TYPE' value in settings.py

     storage_obj should point to a `RelatedFile` Obj

    STORAGE_TYPE;
         'Default': local filesystem -> return filename
         'AWS-S3': Remote Object Store -> Return URL with expire time

    fullpath: return the S3 storage path with aws_location
    """
    # GUARD check for file, return None it missing
    if not hasattr(storage_obj, 'file'):
        return None
    if not storage_obj.file:
        return None

    # Remote storage links (Azure or AWS-S3)
    if settings.STORAGE_TYPE in ['aws-s3', 's3', 'aws', 'azure']:
        if settings.AWS_SHARED_BUCKET or settings.AZURE_SHARED_CONTAINER or fullpath:
            # Return object key for shared S3 bucket
            return os.path.join(
                storage_obj.file.storage.location,
                storage_obj.file.name,
            )
        else:
            # Return Download URL to S3 Object
            return storage_obj.file.storage.url(storage_obj.file.name)

    # Shared FS filename
    else:
        return storage_obj.file.name


class RelatedFile(TimeStampedModel):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    file = models.FileField(help_text=_('The file to store'), upload_to=random_file_name)
    filename = models.CharField(max_length=255, editable=False, default="", blank=True)
    # filehash_md5 = models.CharField(max_length=255, editable=False, default="", blank=True)
    content_type = models.CharField(max_length=255)
    objects = RelatedFileManager()  # ARCH2020 -- Is this actually used??
    store_as_filename = models.BooleanField(default=False, blank=True, null=True)
    groups = models.ManyToManyField(Group, blank=True, null=False, default=None, help_text='Groups allowed to access this object')

    def __str__(self):
        return 'File_{}'.format(self.file)

    def read(self, *args, **kwargs):
        self.file.seek(0)
        return self.file.read(*args, **kwargs)

    def read_json(self, *args, **kwargs):
        self.file.seek(0)
        return json.loads(self.file.read(*args, **kwargs).decode("utf-8"))
