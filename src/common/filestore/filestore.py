import logging
from typing import Union

from oasis_data_manager.errors import OasisException
from oasis_data_manager.filestore.backends.aws_s3 import AwsS3Storage
from oasis_data_manager.filestore.backends.azure_abfs import AzureABFSStorage
from oasis_data_manager.filestore.backends.local import LocalStorage
from oasis_data_manager.filestore.backends.base import BaseStorage


def get_filestore(settings, section='worker', raise_error=True) -> Union[BaseStorage | None]:
    selected_storage = settings.get(section, 'STORAGE_TYPE', fallback="shared-fs").lower()
    if selected_storage in ['local-fs', 'shared-fs']:
        return LocalStorage(
            root_dir=settings.get(section, "MEDIA_ROOT"),
            cache_dir=settings.get(section, 'CACHE_DIR', fallback='/tmp/data-cache'),
        )
    elif selected_storage in ['aws-s3', 'aws', 's3']:
        return AwsS3Storage(
            bucket_name=settings.get(section, 'AWS_BUCKET_NAME'),
            access_key=settings.get(section, 'AWS_ACCESS_KEY_ID', fallback=None),
            secret_key=settings.get(section, 'AWS_SECRET_ACCESS_KEY', fallback=None),
            endpoint_url=settings.get(section, 'AWS_S3_ENDPOINT_URL', fallback=None),
            file_overwrite=settings.getboolean(section, 'AWS_S3_FILE_OVERWRITE', fallback=True),
            object_parameters=settings.get(section, 'AWS_S3_OBJECT_PARAMETERS', fallback={}),
            auto_create_bucket=settings.getboolean(section, 'AWS_AUTO_CREATE_BUCKET', fallback=False),
            default_acl=settings.get(section, 'AWS_DEFAULT_ACL', fallback=None),
            bucket_acl=settings.get(
                section,
                'AWS_BUCKET_ACL',
                fallback=settings.get(section, 'AWS_DEFAULT_ACL', fallback=None),
            ),
            querystring_auth=settings.getboolean(section, 'AWS_QUERYSTRING_AUTH', fallback=False),
            querystring_expire=settings.get(section, 'AWS_QUERYSTRING_EXPIRE', fallback=604800),
            reduced_redundancy=settings.getboolean(section, 'AWS_REDUCED_REDUNDANCY', fallback=False),
            location=settings.get(section, 'AWS_LOCATION', fallback=''),
            encryption=settings.getboolean(section, 'AWS_S3_ENCRYPTION', fallback=False),
            security_token=settings.get(section, 'AWS_SECURITY_TOKEN', fallback=None),
            secure_urls=settings.getboolean(section, 'AWS_S3_SECURE_URLS', fallback=True),
            file_name_charset=settings.get(section, 'AWS_S3_FILE_NAME_CHARSET', fallback='utf-8'),
            gzip=settings.getboolean(section, 'AWS_IS_GZIPPED', fallback=False),
            preload_metadata=settings.getboolean(section, 'AWS_PRELOAD_METADATA', fallback=False),
            url_protocol=settings.get(section, 'AWS_S3_URL_PROTOCOL', fallback='http:'),
            region_name=settings.get(section, 'AWS_S3_REGION_NAME', fallback=None),
            use_ssl=settings.getboolean(section, 'AWS_S3_USE_SSL', fallback=True),
            verify=settings.get(section, 'AWS_S3_VERIFY', fallback=None),
            max_memory_size=settings.get(section, 'AWS_S3_MAX_MEMORY_SIZE', fallback=0),
            shared_bucket=settings.getboolean(section, 'AWS_SHARED_BUCKET', fallback=False),
            aws_log_level=settings.get(section, 'AWS_LOG_LEVEL', fallback=''),
            gzip_content_types=settings.get(section, 'GZIP_CONTENT_TYPES', fallback=(
                'text/css',
                'text/javascript',
                'application/javascript',
                'application/x-javascript',
                'image/svg+xml',
            )),
            cache_dir=settings.get(section, 'CACHE_DIR', fallback='/tmp/data-cache'),
        )
    elif selected_storage in ['azure']:
        return AzureABFSStorage(
            account_name=settings.get(section, 'AZURE_ACCOUNT_NAME'),
            account_key=settings.get(section, 'AZURE_ACCOUNT_KEY'),
            azure_container=settings.get(section, 'AZURE_CONTAINER'),
            location=settings.get(section, 'AZURE_LOCATION', fallback=''),
            connection_string=settings.get(section, 'AZURE_CONNECTION_STRING', fallback=None),
            shared_container=settings.get(section, 'AZURE_SHARED_CONTAINER', fallback=True),
            azure_ssl=settings.get(section, 'AZURE_SSL', fallback=True),
            upload_max_conn=settings.get(section, 'AZURE_UPLOAD_MAX_CONN', fallback=2),
            timeout=settings.get(section, 'AZURE_CONNECTION_TIMEOUT_SECS', fallback=20),
            max_memory_size=settings.get(section, 'AZURE_BLOB_MAX_MEMORY_SIZE', fallback=2 * 1024 * 1024),
            expiration_secs=settings.get(section, 'AZURE_URL_EXPIRATION_SECS', fallback=None),
            overwrite_files=settings.get(section, 'AZURE_OVERWRITE_FILES', fallback=True),
            default_content_type=settings.get(section, 'AZURE_DEFAULT_CONTENT', fallback='application/octet-stream'),
            cache_control=settings.get(section, 'AZURE_CACHE_CONTROL', fallback=None),
            sas_token=settings.get(section, 'AZURE_SAS_TOKEN', fallback=None),
            custom_domain=settings.get(section, 'AZURE_CUSTOM_DOMAIN', fallback=None),
            token_credential=settings.get(section, 'AZURE_TOKEN_CREDENTIAL', fallback=None),
            azure_log_level=settings.get(section, 'AWS_LOG_LEVEL', fallback=logging.ERROR),
            cache_dir=settings.get(section, 'CACHE_DIR', fallback='/tmp/data-cache'),
            endpoint_url=settings.get(section, 'ENDPOINT_URL', fallback=None),
        )
    else:
        if raise_error:
            raise OasisException('Invalid value for STORAGE_TYPE: {}'.format(selected_storage))
        else:
            return None
