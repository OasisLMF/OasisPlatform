from rest_framework.exceptions import ValidationError
from urllib.parse import urlparse
from django.core.files.storage import default_storage
from botocore.exceptions import ClientError as S3_ClientError
from azure.core.exceptions import ResourceNotFoundError as Blob_ResourceNotFoundError
from urllib.request import urlopen
import os
from celery.utils.log import get_task_logger
from tempfile import TemporaryFile
from django.core.files import File
from django.core.files.base import ContentFile
from azure.storage.blob import BlobLeaseClient

from src.server.oasisapi.files.models import RelatedFile
from src.server.oasisapi.files.upload import wait_for_blob_copy

logger = get_task_logger(__name__)


def verify_model_scaling(model):
    if model.run_mode:
        if model.run_mode.lower() == "v1" and model.scaling_options:
            if model.scaling_options.scaling_strategy not in ["QUEUE_LOAD", "FIXED_WORKERS", None]:
                raise ValidationError("Model has invalid scaling setting")


def is_valid_url(url):
    if url:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
    else:
        return False


def is_in_bucket(object_key):
    if not hasattr(default_storage, 'bucket'):
        return False
    else:
        try:
            default_storage.bucket.Object(object_key).load()
            return True
        except S3_ClientError as e:
            if e.response['Error']['Code'] == "404":
                return False
            else:
                raise e


def is_in_container(object_key):
    if not hasattr(default_storage, 'azure_container'):
        return False
    else:
        try:
            blob = default_storage.client.get_blob_client(object_key)
            blob.get_blob_properties()
            return True
        except Blob_ResourceNotFoundError:
            return False


def store_file(reference, content_type, creator, required=True, filename=None):
    """ Returns a `RelatedFile` obejct to store

    :param reference: Storage reference of file (url or file path)
    :type  reference: string

    :param content_type: Mime type of file
    :type  content_type: string

    :param creator: Id of Django user
    :type  creator: int

    :param required: Allow for None returns if set to false
    :type  required: boolean

    :return: Model Object holding a Django file
    :rtype RelatedFile
    """

    # Download data from URL
    if is_valid_url(reference):
        response = urlopen(reference)
        fdata = response.read()

        # Find file name
        header_fname = response.headers.get('Content-Disposition', '').split('filename=')[-1]
        ref = header_fname if header_fname else os.path.basename(urlparse(reference).path)
        fname = filename if filename else ref
        logger.info('Store file: {}'.format(ref))

        # Create temp file, download content and store
        with TemporaryFile() as tmp_file:
            tmp_file.write(fdata)
            tmp_file.seek(0)
            return RelatedFile.objects.create(
                file=File(tmp_file, name=fname),
                filename=fname,
                content_type=content_type,
                creator=creator,
                store_as_filename=True,
            )

    # Issue S3 object Copy
    if is_in_bucket(reference):
        fname = filename if filename else os.path.basename(reference)
        new_file = ContentFile(b'')
        new_file.name = fname
        new_related_file = RelatedFile.objects.create(
            file=new_file,
            filename=fname,
            content_type=content_type,
            creator=creator,
            store_as_filename=True,
        )
        stored_file = default_storage.open(new_related_file.file.name)
        stored_file.obj.copy({"Bucket": default_storage.bucket.name, "Key": reference})
        stored_file.obj.wait_until_exists()
        return new_related_file

    # Issue Azure object Copy
    if is_in_container(reference):
        new_filename = filename if filename else os.path.basename(reference)
        fname = default_storage._get_valid_path(new_filename)
        source_blob = default_storage.client.get_blob_client(reference)
        dest_blob = default_storage.client.get_blob_client(fname)

        try:
            lease = BlobLeaseClient(source_blob)
            lease.acquire()
            dest_blob.start_copy_from_url(source_blob.url)
            wait_for_blob_copy(dest_blob)
            lease.break_lease()
        except Exception as e:
            # copy failed, break file lease and re-raise
            lease.break_lease()
            raise e

        stored_blob = default_storage.open(os.path.basename(fname))
        new_related_file = RelatedFile.objects.create(
            file=File(stored_blob, name=fname),
            filename=fname,
            content_type=content_type,
            creator=creator,
            store_as_filename=True)
        return new_related_file

    try:
        # Copy via shared FS
        ref = str(os.path.basename(reference))
        fname = filename if filename else ref
        return RelatedFile.objects.create(
            file=ref,
            filename=fname,
            content_type=content_type,
            creator=creator,
            store_as_filename=True,
        )
    except TypeError as e:
        if not required:
            logger.warning(f'Failed to store file reference: {reference} - {e}')
            return None
        else:
            raise e


def delete_prev_output(object_model, field_list=[]):
    files_for_removal = list()

    # collect prev attached files
    for field in field_list:
        current_file = getattr(object_model, field)
        if current_file:
            logger.info('delete {}: {}'.format(field, current_file))
            setattr(object_model, field, None)
            files_for_removal.append(current_file)

    # Clear fields
    object_model.save(update_fields=field_list)

    # delete old files
    for f in files_for_removal:
        f.delete()
