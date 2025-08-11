from django.db.backends.postgresql.base import DatabaseWrapper as PostgresDatabaseWrapper
from azure.identity import ClientSecretCredential
import psycopg


class DatabaseWrapper(PostgresDatabaseWrapper):
    def __init__(self, settings_dict, alias='default'):
        super().__init__(settings_dict, alias)
        self.settings_dict = settings_dict  # Store settings for later use
        self.credential = None  # Initialize credential object

    def get_azure_access_token(self):
        """
        Fetches a fresh access token using Azure Service Principal credentials.
        """
        settings = self.settings_dict
        tenant_id = settings.get('TENANT_ID')
        client_id = settings.get('CLIENT_ID')
        client_secret = settings.get('CLIENT_SECRET')

        if not all([tenant_id, client_id, client_secret]):
            raise ValueError("Azure AD credentials are missing in DATABASES settings.")

        # Initialize credential object only once
        if self.credential is None:
            self.credential = ClientSecretCredential(tenant_id, client_id, client_secret)

        # Fetch a fresh token
        token = self.credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
        return token.token

    def get_new_connection(self, conn_params):
        """
        Establish a new PostgreSQL connection with a fresh Azure AD token.
        """
        conn_params["password"] = self.get_azure_access_token()  # Get fresh token
        conn_params["sslmode"] = "require"  # Ensure SSL connection

        return psycopg.connect(**conn_params)
