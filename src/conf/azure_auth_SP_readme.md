# Celery Configuration with Azure Service Principal for PostgreSQL Backend

## Overview
This setup enables Celery to store task results in Azure PostgreSQL while authenticating securely using Azure Active Directory Service Principal (SP). This eliminates the need for database passwords, enhances security, and ensures seamless authentication with Azure PostgreSQL using Service Principal tokens

- Instead of a static username/password, it retrieves an Azure AD access token dynamically.
- The token auto-refreshes every 60 minutes to maintain authentication.
- Logs are sanitized to prevent token exposure.

### Configuration Breakdown


```/var/www/oasis/
│── src/
│   ├── conf/
│   │   ├── celeryconf.py
│   │   ├── utils.py  # Configures celery backend logic for Service Principal authentication
│   ├── server
│   │   ├── oasisapi
│   │   │   ├── settings.py  # where we Configures server database backend
```


##### utils.py - Handling Azure AD Token Authentication
This module is responsible for fetching Azure Active Directory access tokens and managing the PostgreSQL connection for Celery.

<details>
  <summary>Environment Variables Required (Click to expand)</summary>

| Variable Name                       | Description                                    |
|--------------------------------------|------------------------------------------------|
| `AZURE_TENANT_ID`                    | Azure AD Tenant ID                             |
| `AZURE_CLIENT_ID`                    | Azure Service Principal Client ID             |
| `AZURE_CLIENT_SECRET`                | Azure Service Principal Client Secret         |
| `AZURE_SERVICE_PRINCIPAL_USER`        | Username for PostgreSQL (e.g., `sp_user@db`)  |
| `CELERY_RESULTS_DB_BACKEND`           | Database backend (e.g., `db+postgresql`)      |
| `DB_HOST`                             | PostgreSQL database host                      |
| `DB_PORT`                             | PostgreSQL database port                      |
| `DB_NAME`                             | Celery result backend database name           |

</details>


#### Troubleshooting
- Error: Azure AD credentials are missing for Celery DB
- Ensure AZURE_TENANT_ID, AZURE_CLIENT_ID, and AZURE_CLIENT_SECRET are set correctly.
- Celery fails to connect to PostgreSQL
- Verify that the Service Principal is assigned the correct roles (db_owner or db_reader).
- Expired Token Error
- Restart the worker to refresh the token.
