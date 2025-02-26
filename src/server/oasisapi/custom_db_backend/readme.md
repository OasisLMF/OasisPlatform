# Azure Service Principal for PostgreSQL Authentication

#### Defining custom DB Engine for Azure Service Principal Authentication
#### Tree 

```/var/www/oasis/
│── src/
│   ├── server/
│   │   ├── oasisapi/
│   │   │   ├── settings.py  # Configures database backend
│   │   │   ├── custom_db_backend/
│   │   │   │   ├── __init__.py  # existing
│   │   │   │   ├── readme.md  # Defining the custom DB Engine
│   │   │   │   ├── base/
│   │   │   │   |    ├── base.py  # where we have the DatabaseWrapper
│   │   │   │   |    ├── __init__.py  # existing
```

## Overview
This document explains how to implement **Azure Service Principal Authentication** with **token refresh** for a **Django application** using **PostgreSQL** as the authentication backend. The goal is to authenticate applications securely while enabling token renewal for continuous access.

#### Key Components
1. **Azure Service Principal**: A non-human identity used by applications to authenticate and authorize access to Azure resources.
2. **PostgreSQL Database**: A database-driven authentication system that stores service principal credentials and permissions.
3. **Custom PostgreSQL Database Wrapper**: Extends Django’s default PostgreSQL database backend to authenticate using Azure AD tokens.

#### Architecture
1. **Service Principal Registration**: Store client ID, hashed secret, and permissions in PostgreSQL.
2. **Authentication Flow**:
   - The application sends authentication requests with client ID and secret.
   - The Django authentication wrapper validates credentials against the database.
   - On success, an access token and a refresh token are issued.
3. **Token Refresh Flow**:
   - The application sends a refresh request with a valid refresh token.
   - The wrapper validates the refresh token and issues a new access token.
4. **Database Authentication via Azure AD**:
   - The custom database wrapper fetches a fresh Azure AD token for database authentication.

#### Implementation Steps
##### 1. *_Custom settings.py_*

```python
# For Azure Service Principal Authentication with token rotation

    DATABASES = {
       'default': {
           'ENGINE': DB_ENGINE,
           'NAME': iniconf.settings.get('server', 'db_name'),
           'USER': iniconf.settings.get('server', 'AZURE_SERVICE_PRINCIPAL_USER'),
           'PASSWORD': '', # Database-Custom-backendWrapper.get_token
           'HOST': iniconf.settings.get('server', 'db_host'),
           'PORT': iniconf.settings.get('server', 'db_port'),
           'TENANT_ID': iniconf.settings.get('server','AZURE_TENANT_ID', fallback=None),
           'CLIENT_ID': iniconf.settings.get('server','AZURE_CLIENT_ID', fallback=None),
           'CLIENT_SECRET': iniconf.settings.get('server','AZURE_CLIENT_SECRET', fallback=None),
           }
        }
```

##### 2. Custom Database Backend (base.py)
Create a custom database backend that authenticates using Azure AD.

```python
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
```


### Security Best Practices followed
- **Short-Lived Access Tokens**: Implement tokens with a short expiration time and refresh capability.
- **Access Control**: Enforce fine-grained permissions stored in PostgreSQL.
- **Secure Database Connection**: Enforce SSL and use short-lived Azure AD tokens for authentication.

## Conclusion
This implementation provides a secure way to authenticate Azure service principals using a Django application with PostgreSQL while enabling token refresh for uninterrupted access. The custom database backend ensures secure connections using Azure AD authentication.

