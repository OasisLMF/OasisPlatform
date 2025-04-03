from azure.identity import ClientSecretCredential
import psycopg2
import time  # To track token expiration

class CeleryDatabaseBackend:
    def __init__(self, settings):
        self.settings = settings
        self.credential = None
        self.token = None
        self.token_expiry = 0  # Stores expiry timestamp

    def get_azure_access_token(self):
        """
        Fetches and caches a fresh access token using Azure Service Principal credentials.
        Auto-refreshes when token is about to expire.
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

    def get_connection(self):
        """
        Establish a PostgreSQL connection for Celery using an Azure AD token.
        """
        conn_params = {
            "dbname": self.settings.get('celery', 'db_name'),
            "user": self.settings.get('celery', 'AZURE_SERVICE_PRINCIPAL_USER'),
            "password": self.get_azure_access_token(),
            "host": self.settings.get('celery', 'db_host'),
            "port": self.settings.get('celery', 'db_port'),
            "sslmode": "require",
        }

        return psycopg2.connect(**conn_params)

    def get_db_engine(self):
        """
        Retrieves the database engine type from settings.
        Ensures correct format for Celery result backend.
        """
        db_engine = self.settings.get("celery", "DB_ENGINE", fallback="db+sqlite")

        if db_engine.startswith("db+postgresql"):
            return "postgresql+psycopg2"  # Ensure correct format for Celery backend

        return db_engine
