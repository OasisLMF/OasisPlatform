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

       # S3 storage links
       if settings.STORAGE_TYPE in ['aws-s3', 's3', 'aws']:
           if settings.AWS_SHARED_BUCKET or fullpath:
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
           #if fullpath:
           #    return os.path.join(
           #        storage_obj.file.storage.location,
           #        storage_obj.file.name,
           #    )    
           return storage_obj.file.name


class RelatedFile(TimeStampedModel):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    file = models.FileField(help_text=_('The file to store'), upload_to=random_file_name)
    filename = models.CharField(max_length=255, editable=False, default="", blank=True)
    # filehash_md5 = models.CharField(max_length=255, editable=False, default="", blank=True)
    content_type = models.CharField(max_length=255)
    store_as_filename = models.BooleanField(default=False, blank=True, null=True)

    def __str__(self):
        return 'File_{}'.format(self.file)

    def read(self, *args, **kwargs):
        return self.file.read(*args, **kwargs)
