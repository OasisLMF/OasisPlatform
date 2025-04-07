from azure.identity import ClientSecretCredential
import time  # To track token expiration


class CeleryAzureServicePrincipal:
    def __init__(self, settings):
        self.settings = settings
        self.credential = None
        self.token = None
        self.token_expiry = 0  # Stores expiry timestamp

    def get_access_token(self):
        """
        Fetches and caches a fresh access token using Azure Service Principal credentials.
        """
        tenant_id = self.settings.get('celery', 'AZURE_TENANT_ID')
        client_id = self.settings.get('celery', 'AZURE_CLIENT_ID')
        client_secret = self.settings.get('celery', 'AZURE_CLIENT_SECRET')

        if not all([tenant_id, client_id, client_secret]):
            raise ValueError("Azure AD credentials are missing for Celery DB.")

        if self.credential is None:
            self.credential = ClientSecretCredential(tenant_id, client_id, client_secret)

        # Refresh token if expired or close to expiration
        current_time = time.time()
        if self.token is None or current_time >= self.token_expiry - 300:  # Refresh 5 min before expiry
            token_response = self.credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
            self.token = token_response.token
            self.token_expiry = current_time + 3600  # Azure tokens last ~60 min

        return self.token
