import os
import json
from io import BytesIO

import pandas as pd
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.files import File
from django.db import models
from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel
from rest_framework.reverse import reverse


def related_file_to_df(RelatedFile):
    if not RelatedFile:
        return None
    RelatedFile.file.seek(0)
    if RelatedFile.content_type == 'application/octet-stream':
        return pd.read_parquet(BytesIO(RelatedFile.read()))
    else:
        return pd.read_csv(BytesIO(RelatedFile.read()))


def random_file_name(instance, filename):
    if getattr(instance, "store_as_filename", False):
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

    storage_file = (
        storage_obj.converted_file
        if storage_obj.converted_file and storage_obj.conversion_status == RelatedFile.ConversionState.DONE else
        storage_obj.file
    )

    # Remote storage links (Azure or AWS-S3)
    if settings.STORAGE_TYPE in ['aws-s3', 's3', 'aws', 'azure']:
        if settings.AWS_SHARED_BUCKET or settings.AZURE_SHARED_CONTAINER or fullpath:
            # Return object key for shared S3 bucket
            return os.path.join(
                storage_file.storage.location,
                storage_file.name,
            )
        else:
            # Return Download URL to S3 Object
            return storage_file.storage.url(storage_file.name)

    # Shared FS filename
    else:
        return storage_file.name


class MappingFile(models.Model):
    name = models.CharField(max_length=255, default="")
    description = models.TextField(default="", blank=True)
    file = models.FileField(upload_to=random_file_name)
    input_validation_file = models.FileField(upload_to=random_file_name, null=True, blank=True, default=None)
    output_validation_file = models.FileField(upload_to=random_file_name, null=True, blank=True, default=None)
    groups = models.ManyToManyField(Group, blank=True, null=False, default=None, help_text='Groups allowed to access this object')

    def get_absolute_conversion_file_url(self, request):
        return (
            reverse('mapping-file-conversion-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)
            if self.file else
            None
        )

    def get_absolute_input_validation_file_url(self, request):
        return (
            reverse('mapping-file-input-validation-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)
            if self.input_validation_file else
            None
        )

    def get_absolute_output_validation_file_url(self, request):
        return (
            reverse('mapping-file-output-validation-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)
            if self.output_validation_file else
            None
        )


class RelatedFile(TimeStampedModel):
    class ConversionState(TextChoices):
        NONE = "NONE", _("None")
        PENDING = "PENDING", _("Pending")
        IN_PROGRESS = "IN_PROGRESS", _("In Progress")
        DONE = "DONE", _("Done")
        ERROR = "ERROR", _("Error")

        @classmethod
        def is_ready(cls, state):
            return state in [cls.NONE, cls.ERROR, cls.DONE]

    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    file = models.FileField(help_text=_('The file to store'), upload_to=random_file_name)
    filename = models.CharField(max_length=255, editable=False, default="", blank=True)
    content_type = models.CharField(max_length=255)
    store_as_filename = models.BooleanField(default=False, blank=True, null=True)
    groups = models.ManyToManyField(Group, blank=True, null=False, default=None, help_text='Groups allowed to access this object')
    oed_validated = models.BooleanField(default=False, editable=False)

    mapping_file = models.ForeignKey(MappingFile, blank=True, default=None, null=True, on_delete=models.CASCADE, related_name="mapped_files")
    converted_file = models.FileField(help_text=_('The file to store after conversion'), upload_to=random_file_name, default=None, null=True, blank=True)
    conversion_log_file = models.FileField(upload_to=random_file_name, default=None, null=True, blank=True)
    converted_filename = models.CharField(max_length=255, editable=False, default="", blank=True)
    conversion_time = models.DateTimeField(help_text=_('The time the last conversion was started'), null=True, default=None, blank=True, editable=False)
    conversion_state = models.CharField(max_length=11, choices=ConversionState.choices, default=ConversionState.NONE)

    objects = RelatedFileManager()  # ARCH2020 -- Is this actually used??

    def __str__(self):
        return 'File_{}'.format(self.file)

    def get_absolute_conversion_log_file_url(self, request):
        return (
            reverse('file-conversion-log-file', kwargs={'version': 'v1', 'pk': self.pk}, request=request)
            if self.conversion_log_file else
            None
        )

    def read(self, *args, **kwargs):
        self.file.seek(0)
        return self.file.read(*args, **kwargs)

    def read_json(self, *args, **kwargs):
        self.file.seek(0)
        return json.loads(self.file.read(*args, **kwargs).decode("utf-8"))

    def start_conversion(self, mapping_file):
        from src.server.oasisapi.files.tasks import run_file_conversion

        self.mapping_file = mapping_file
        self.conversion_state = RelatedFile.ConversionState.PENDING
        self.save()

        run_file_conversion.delay(self.id)
