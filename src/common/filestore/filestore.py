from oasislmf.utils.exceptions import OasisException
from ...conf.iniconf import settings
from .backends.aws_storage import AwsObjectStore
from .backends.azure_storage import AzureObjectStore
from .backends.storage_manager import BaseStorageConnector


def get_filestore():
    selected_storage = settings.get('worker', 'STORAGE_TYPE', fallback="").lower()
    if selected_storage in ['local-fs', 'shared-fs']:
        return BaseStorageConnector(settings)
    elif selected_storage in ['aws-s3', 'aws', 's3']:
        return AwsObjectStore(settings)
    elif selected_storage in ['azure']:
        return AzureObjectStore(settings)
    else:
        raise OasisException('Invalid value for STORAGE_TYPE: {}'.format(selected_storage))