
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import (
    BlobClient, BlobSasPermissions, BlobServiceClient, ContentSettings,
    generate_blob_sas,
)

from ..storage_manager import BaseStorageConnector

class AzureObjectStore(BaseStorageConnector):

    def __init__(self, settings):
        self._service_client = None
        self._client = None

        # Required
        self.account_name       = settings.get('worker', 'AZURE_ACCOUNT_NAME')
        self.account_key        = settings.get('worker', 'AZURE_ACCOUNT_KEY')
        self.azure_container    = settings.get('worker', 'AZURE_CONTAINER')
        self.connection_string  = settings.get('worker', 'AZURE_CONNECTION_STRING')

        # Optional
        self.location             = settings.get('worker', 'AZURE_LOCATION', fallback='')
        self.shared_container     = settings.get('worker', 'AZURE_SHARED_CONTAINER', fallback=True)
        self.azure_ssl            = settings.get('worker', 'AZURE_SSL', fallback=True)
        self.upload_max_conn      = settings.get('worker', 'AZURE_UPLOAD_MAX_CONN', fallback=2)
        self.timeout              = settings.get('worker', 'AZURE_CONNECTION_TIMEOUT_SECS', fallback=20)
        self.max_memory_size      = settings.get('worker', 'AZURE_BLOB_MAX_MEMORY_SIZE', fallback=2*1024*1024)
        self.expiration_secs      = settings.get('worker', 'AZURE_URL_EXPIRATION_SECS', fallback=None)
        self.overwrite_files      = settings.get('worker', 'AZURE_OVERWRITE_FILES', fallback=True)
        self.default_content_type = settings.get('worker', 'AZURE_DEFAULT_CONTENT', fallback='application/octet-stream')
        self.cache_control        = settings.get('worker', 'AZURE_CACHE_CONTROL', fallback=None)
        self.sas_token            = settings.get('worker', 'AZURE_SAS_TOKEN', fallback=None)
        self.custom_domain        = settings.get('worker', 'AZURE_CUSTOM_DOMAIN', fallback=None)
        self.token_credential     = settings.get('worker', 'AZURE_TOKEN_CREDENTIAL', fallback=None)

  def _get_service_client(self):
        if self.connection_string is not None:
            return BlobServiceClient.from_connection_string(self.connection_string)

        account_domain = self.custom_domain or "{}.blob.core.windows.net".format(
            self.account_name
        )
        account_url = "{}://{}".format(self.azure_protocol, account_domain)

        credential = None
        if self.account_key:
            credential = {
                "account_name": self.account_name,
                "account_key": self.account_key,
            }
        elif self.sas_token:
            credential = self.sas_token
        elif self.token_credential:
            credential = self.token_credential
        return BlobServiceClient(account_url, credential=credential)

    @property
    def service_client(self):
        if self._service_client is None:
            self._service_client = self._get_service_client()
        return self._service_client

    @property
    def client(self):
        if self._client is None:
            self._client = self.service_client.get_container_client(
                self.azure_container
            )
        return self._client



    def _fetch_file(self, reference, output_dir=""):
        pass

    def _store_file(self, file_path, suffix=None):
        pass

    def _store_dir(self, directory_path, suffix=None, arcname=None):
        pass

    def upload(self, object_name, filepath, ExtraArgs=None):
        pass

    def url(self, object_name, parameters=None, expire=None):
        pass
