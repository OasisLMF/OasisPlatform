import bz2
import csv
import gzip
import io
import lzma
import os
import json
from io import BytesIO

import pandas as pd
import pyarrow.parquet as pq
import tarfile
import zipfile
from urllib.parse import urlparse
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.files import File
from django.db import models
from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel
from oasis_data_manager.filestore.archive import ZSTD_MAGIC
from rest_framework.reverse import reverse


def related_file_to_df(RelatedFile):
    if not RelatedFile:
        return None
    RelatedFile.file.seek(0)
    if RelatedFile.content_type == 'application/octet-stream':
        return pd.read_parquet(BytesIO(RelatedFile.read()))
    else:
        return pd.read_csv(BytesIO(RelatedFile.read()))


# --- Worker directory archives ---
# Run/output directories are tarred by the workers and compressed as gzip or
# zstd (ARCHIVE_COMPRESSION_TYPE)
ARCHIVE_CONTENT_TYPES = {'tar.gz': 'application/gzip', 'tar.zst': 'application/zstd'}


def archive_suffix(reference):
    """ Suffix of a worker archive from its storage reference (key, path or URL), 'tar.gz' unless it's 'tar.zst' """
    return 'tar.zst' if urlparse(str(reference)).path.endswith('.tar.zst') else 'tar.gz'


def _zstd_decompress(data):
    """ Decompress zstd bytes, stdlib on Python 3.14+, else the zstandard package """
    try:
        from compression import zstd
        return zstd.decompress(data)
    except ImportError:
        import zstandard
        with zstandard.ZstdDecompressor().stream_reader(BytesIO(data)) as reader:
            return reader.read()


def _open_worker_archive(RelatedFile):
    """ Open a worker archive (tar, optionally gzip or zstd compressed) for random access.

    tarfile detects gzip itself, only zstd needs decompressing first. The whole
    archive is read into memory as members are looked up by name
    """
    data = RelatedFile.read()
    if data[:len(ZSTD_MAGIC)] == ZSTD_MAGIC:
        data = _zstd_decompress(data)
    return tarfile.open(fileobj=BytesIO(data), mode='r')


def list_tar_file(RelatedFile):
    if not RelatedFile:
        return None

    tarf = _open_worker_archive(RelatedFile)

    files = [m.name for m in tarf.getmembers() if m.isfile()]
    return files


def extract_file_from_tar(RelatedFile, fname):
    if not RelatedFile:
        return None

    tarf = _open_worker_archive(RelatedFile)

    return tarf.extractfile(fname)


# --- Uploaded portfolio files ---

def _open_decompressed_upload(fileobj):
    """ Wrap an uploaded single-file input (e.g. a location CSV) in a streaming
    decompressor for gzip, bz2, xz or single-entry zip, detected from its magic bytes.
    Uncompressed files are returned as-is.

    Content type can't be relied on, e.g. 'loc.csv.gz' is inferred as 'text/csv'
    """
    fileobj.seek(0)
    magic = fileobj.read(6)
    fileobj.seek(0)
    if magic.startswith(b'\x1f\x8b'):
        return gzip.GzipFile(fileobj=fileobj, mode='rb')
    if magic.startswith(b'BZh'):
        return bz2.BZ2File(fileobj, mode='rb')
    if magic.startswith(b'\xfd7zXZ\x00'):
        return lzma.LZMAFile(fileobj, mode='rb')
    if magic.startswith(b'PK\x03\x04'):
        zf = zipfile.ZipFile(fileobj)
        names = zf.namelist()
        if len(names) != 1:
            raise ValueError(f'Expected a single file in zip archive, found {len(names)}')
        return zf.open(names[0])
    return fileobj


def related_file_row_count(RelatedFile):
    """ Count data rows without loading the file into a DataFrame.

    Parquet reads the count from the footer metadata, CSV (optionally gzip, bz2,
    xz or zip compressed) is streamed, skipping the header and blank lines
    to match pd.read_csv
    """
    if not RelatedFile:
        return None
    RelatedFile.file.seek(0)
    if RelatedFile.content_type == 'application/octet-stream' or RelatedFile.file.read(4) == b'PAR1':
        RelatedFile.file.seek(0)
        return pq.ParquetFile(RelatedFile.file).metadata.num_rows

    stream = _open_decompressed_upload(RelatedFile.file)
    text = io.TextIOWrapper(stream, encoding='utf-8', newline='')
    try:
        rows = sum(1 for row in csv.reader(text) if row)
    finally:
        # Don't let the wrapper close the underlying file
        text.detach()
        if stream is not RelatedFile.file:
            stream.close()
    return max(rows - 1, 0)


def random_file_name(instance, filename):
    if getattr(instance, "store_as_filename", False):
        return filename

    # Work around: S3 objects pushed as '<hash>.gz' should be '<hash>.tar.gz'
    if filename.endswith(('.tar.gz', '.tar.zst')):
        ext = '.tar.' + filename.rsplit('.', 1)[-1]
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
        if storage_obj.converted_file and storage_obj.conversion_state == RelatedFile.ConversionState.DONE else
        storage_obj.file
    )

    # Remote storage links (Azure or AWS-S3)
    if settings.STORAGE_TYPE in settings.AWS_S3 + settings.AZURE:
        shared_storage = (
            settings.AWS_SHARED_BUCKET
            if settings.STORAGE_TYPE in settings.AWS_S3 else
            settings.AZURE_SHARED_CONTAINER
        )
        if shared_storage or fullpath:
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

    def get_absolute_conversion_file_url(self, request, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return (
            reverse(f'{override_ns}mapping-file-conversion-file', kwargs={'pk': self.pk}, request=request)
            if self.file else
            None
        )

    def get_absolute_input_validation_file_url(self, request, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return (
            reverse(f'{override_ns}mapping-file-input-validation-file', kwargs={'pk': self.pk}, request=request)
            if self.input_validation_file else
            None
        )

    def get_absolute_output_validation_file_url(self, request, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return (
            reverse(f'{override_ns}mapping-file-output-validation-file', kwargs={'pk': self.pk}, request=request)
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
    groups = models.ManyToManyField(Group, blank=True, default=None, help_text='Groups allowed to access this object')
    oed_validated = models.BooleanField(default=False, editable=False)

    mapping_file = models.ForeignKey(MappingFile, blank=True, default=None, null=True, on_delete=models.CASCADE, related_name="mapped_files")
    converted_file = models.FileField(help_text=_('The file to store after conversion'),
                                      upload_to=random_file_name, default=None, null=True, blank=True)
    conversion_log_file = models.FileField(upload_to=random_file_name, default=None, null=True, blank=True)
    converted_filename = models.CharField(max_length=255, editable=False, default="", blank=True)
    conversion_time = models.DateTimeField(help_text=_('The time the last conversion was started'),
                                           null=True, default=None, blank=True, editable=False)
    conversion_state = models.CharField(max_length=11, choices=ConversionState.choices, default=ConversionState.NONE)

    objects = RelatedFileManager()  # ARCH2020 -- Is this actually used??

    def __str__(self):
        return 'File_{}'.format(self.file)

    def get_absolute_conversion_log_file_url(self, request, namespace=None):
        override_ns = f'{namespace}:' if namespace else ''
        return (
            reverse(f'{override_ns}file-conversion-log-file', kwargs={'pk': self.pk}, request=request)
            if self.conversion_log_file else
            None
        )

    def read(self, *args, **kwargs):
        self.file.seek(0)
        return self.file.read(*args, **kwargs)

    def read_json(self, *args, **kwargs):
        self.file.seek(0)
        return json.loads(self.file.read(*args, **kwargs).decode("utf-8"))

    def start_conversion(self, mapping_file, version="v2"):
        from src.server.oasisapi.files.v1_api.tasks import run_file_conversion as v1_run
        from src.server.oasisapi.files.v2_api.tasks import run_file_conversion as v2_run

        task = {
            "v1": v1_run,
            "v2": v2_run,
        }.get(version, v2_run)

        self.mapping_file = mapping_file
        self.conversion_state = RelatedFile.ConversionState.PENDING
        self.save()

        task.delay(self.id)
