Container Configuration
======================

.. _container_configuration:

:doc:`/explanation/overview` | :doc:`/explanation/platform_architecture` | :doc:`/how-to/container_configuration` | :doc:`/reference/rest_api` | :doc:`/how-to/distributed_execution` | :doc:`/how-to/distributed_configuration`

There are two methods for setting configuration options on an oasis container. (1) by setting a shell environment variable on the container. (2) by adjusting a conf.ini file within the container.

Environment Variable Overrides
------------------------------

Configuration for OASIS Docker containers is primarily managed via a conf.ini file, which establishes default values. However, the **preferred and highest-precedence method for dynamic configuration is through shell environment variables.**

Naming Convention
^^^^^^^^^^^^^^^^^

To ensure an environment variable is recognized and applied, it must be prefixed with **OASIS_**. Any environment variable lacking this prefix will be ignored by the OASIS applications.

* **Example:** Setting OASIS_DEBUG=True will override the default DEBUG=False value found in the conf.ini file.

conf.ini Location and Loading
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The canonical conf.ini file is located at OasisLMF/OasisPlatform/conf.ini within the OasisPlatform repository. This file provides the base configuration, but its effective path and how it's consumed differs based on the container type:

* **Model Worker Images:**

  * **Container Path:** /home/worker/conf.ini
  * **Integration:** Values from this conf.ini are loaded and directly influence the configuration within Celery's task processing files.

* **Server Images (Django):**

  * **Container Path:** /var/www/oasis/conf.ini
  * **Integration:** Values from this conf.ini are loaded into Django's settings.py configuration file, forming the application's core settings.

Precedence Hierarchy
^^^^^^^^^^^^^^^^^^^^

When an OASIS container starts, configuration values are applied in the following order of precedence, with later steps overriding earlier ones:

1. **conf.ini Defaults:** Values read from the conf.ini file ([default], [server], [worker], [celery] sections, respecting section-specific overrides).
2. **OASIS_ Prefixed Environment Variables:** Any environment variable set with the OASIS_ prefix (e.g., OASIS_DEBUG) will *always* override a corresponding setting derived from the conf.ini file.

This ensures that you can define sensible defaults within your image, while maintaining the flexibility to adjust specific parameters at deployment time using environment variables, without needing to rebuild or modify the container image itself.

Understanding conf.ini Structure and Precedence
-----------------------------------------------

The conf.ini file employs a standard INI file format, organized into sections, each containing key-value pairs. The sections define the scope of the configuration:

* **[default]**: This section contains settings that apply universally to all container types (servers and workers).
* **[server]**: Settings in this section are specific to server (e.g., Django) containers. Any key-value pair defined here will override a similarly named key in the [default] section when accessed by a server.
* **[worker]**: Similar to [server], this section holds configurations unique to worker containers. Settings here will override [default] settings for workers.
* **[celery]**: This section is dedicated to Celery-specific configuration options and applies to *both* server and worker container types, assuming both might interact with Celery.

Precedence Rules
^^^^^^^^^^^^^^^

1. **Environment Variables (Highest Precedence):** An environment variable OASIS_SETTING_NAME_TO_GET=<value> will always override any setting, regardless of the conf.ini file. This provides the most dynamic and immediate way to adjust configurations without modifying the file itself.
2. **Specific Section Overrides Default:** For server containers, values in [server] take precedence over [default]. For worker containers, values in [worker] take precedence over [default].
3. **[celery] Section:** Settings within [celery] are additive and specifically for Celery. They don't directly override [default], [server], or [worker] in the same way, but rather provide a dedicated namespace for Celery configurations that both server and worker processes can utilize.

Server Container Configuration Options
--------------------------------------

These options are specifically applicable to the **coreoasis/api_server** containers and can be set via environment variables (prefixed with OASIS_, OASIS_{ini sections}_{variable}) or within the conf.ini file's [server] or [default] sections.

For example OASIS_DB_PASS=<value> or OASIS_SERVER_DB_PASS=<value> will both work.

Django Core Options
^^^^^^^^^^^^^^^^^^^

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "MEDIA_ROOT", "String", "(Django default)", "The absolute filesystem path to the directory that will hold user-uploaded media files."
   "SECRET_KEY", "String", "(Django required)", "A secret key used for cryptographic signing, crucial for security (e.g., sessions, password resets)."
   "ALLOWED_HOSTS", "List/String", "[]", "A list of strings representing the host/domain names that this Django site can serve. Protects against HTTP Host header attacks."
   "STARTUP_RUN_MIGRATIONS", "Boolean", "True", "If set to True, Django database migrations will be automatically applied when the container starts."
   "OASIS_ADMIN_USER", "String", "None", "If set, a default Django superuser will be created with this username. Requires OASIS_ADMIN_PASS."
   "OASIS_ADMIN_PASS", "String", "None", "The password for the default admin user specified by OASIS_ADMIN_USER. Requires OASIS_ADMIN_USER."

Debug Options
^^^^^^^^^^^^

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "DEBUG", "Boolean", "False", "Controls Django's debug mode. If True, enables verbose logging, error pages, and other development features. **Should be False in production.**"
   "DEBUG_TOOLBAR", "Boolean", "False", "If True, enables the Django Debug Toolbar, typically accessible in the Swagger UI for development and debugging purposes."
   "URL_SUB_PATH", "Boolean", "False", "If True, all REST API routes will be nested under a /api/ sub-path (e.g., https://<site-domain>/api/). Otherwise, routes are directly under the domain (e.g., https://<site-domain>/)."
   "DISABLE_V2_API", "Boolean", "False", "If True, disables the V2 API routes, primarily for backward compatibility with older client integrations."

Storage Related Options
^^^^^^^^^^^^^^^^^^^^^^^

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "PORTFOLIO_PARQUET_STORAGE", "Boolean", "False", "If True, all portfolio CSV files uploaded will be automatically compressed and stored in Parquet format."
   "STORAGE_TYPE", "String", "shared-fs", "Defines the backend storage solution. Valid values are 'S3' (AWS S3), 'AZURE' (Azure Blob Storage), or 'shared-fs' (a common file system accessible by containers)."

**If STORAGE_TYPE is 'S3', the following options are valid:**

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "AWS_ACCESS_KEY_ID", "String", "None", "Your AWS access key ID. Required for S3 authentication."
   "AWS_SECRET_ACCESS_KEY", "String", "None", "Your AWS secret access key. Required for S3 authentication."
   "AWS_STORAGE_BUCKET_NAME", "String", "None", "The name of the S3 bucket where files will be stored."
   "AWS_DEFAULT_ACL", "String", "private", "The default Access Control List (ACL) to apply to uploaded objects (e.g., 'private', 'public-read')."
   "AWS_S3_CUSTOM_DOMAIN", "String", "None", "A custom domain to use for accessing S3 objects (e.g., cdn.example.com)."
   "AWS_S3_ENDPOINT_URL", "String", "None", "Custom endpoint URL for S3, useful for S3-compatible storage solutions (e.g., MinIO)."
   "AWS_LOCATION", "String", "None", "The base path or directory within the S3 bucket where files will be stored."
   "AWS_S3_REGION_NAME", "String", "us-east-1", "The AWS region name for your S3 bucket (e.g., eu-west-2)."
   "AWS_LOG_LEVEL", "String", "INFO", "Logging level for AWS S3 operations (e.g., DEBUG, INFO, WARNING, ERROR)."
   "AWS_QUERYSTRING_AUTH", "Boolean", "True", "If True, generated URLs for S3 objects will include query string authentication."
   "AWS_QUERYSTRING_EXPIRE", "Integer", "3600", "The expiration time in seconds for signed S3 URLs."
   "AWS_SHARED_BUCKET", "String", "None", "(Inferred) Specifies a shared S3 bucket name if multiple components access the same shared storage."

**If STORAGE_TYPE is 'AZURE', the following options are valid:**

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "AZURE_ACCOUNT_NAME", "String", "None", "Your Azure Storage account name. Required for Azure Blob Storage."
   "AZURE_ACCOUNT_KEY", "String", "None", "Your Azure Storage account key. Required for Azure Blob Storage."
   "AZURE_CONTAINER", "String", "None", "The name of the Azure Blob Storage container where files will be stored."
   "AZURE_LOCATION", "String", "None", "The base path or virtual directory within the Azure container where files will be stored."
   "AZURE_SHARED_CONTAINER", "String", "None", "(Inferred) Specifies a shared Azure container name if multiple components access the same shared storage."
   "AZURE_OVERWRITE_FILES", "Boolean", "False", "If True, uploaded files will overwrite existing files with the same name in Azure Blob Storage."
   "AZURE_LOG_LEVEL", "String", "INFO", "Logging level for Azure Blob Storage operations."
   "AZURE_SSL", "Boolean", "True", "If True, secure SSL connections will be used for Azure Blob Storage."
   "AZURE_UPLOAD_MAX_CONN", "Integer", "2", "The maximum number of concurrent connections to use for Azure Blob uploads."
   "AZURE_CONNECTION_TIMEOUT_SECS", "Integer", "20", "The timeout in seconds for Azure Blob Storage connections."
   "AZURE_BLOB_MAX_MEMORY_SIZE", "Integer", "2097152", "The maximum memory in bytes to use when buffering data for Azure blobs."
   "AZURE_URL_EXPIRATION_SECS", "Integer", "3600", "The expiration time in seconds for generated shared access signature (SAS) URLs for Azure blobs."
   "AZURE_CONNECTION_STRING", "String", "None", "A full Azure Storage connection string. Can be used as an alternative to AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY."
   "AZURE_TOKEN_CREDENTIAL", "String", "None", "(Inferred) A token credential for authentication with Azure Blob Storage, typically for OAuth/Managed Identity."
   "AZURE_CACHE_CONTROL", "String", "None", "Value for the Cache-Control header on uploaded Azure blobs."
   "AZURE_OBJECT_PARAMETERS", "JSON/String", "None", "(Inferred) Additional parameters to apply to Azure blob objects on upload, typically as a JSON string."

Server Database (DB) Options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "DB_ENGINE", "String", "django.db.backends.postgresql", "The database backend engine (e.g., django.db.backends.postgresql, django.db.backends.mysql)."
   "DB_HOST", "String", "localhost", "The hostname or IP address of the database server."
   "DB_PASS", "String", "None", "The password for the database user."
   "DB_USER", "String", "None", "The username for connecting to the database."
   "DB_NAME", "String", "oasis", "The name of the database to connect to."
   "DB_PORT", "Integer", "5432", "The port number on which the database server is listening. (e.g., 5432 for PostgreSQL, 3306 for MySQL)."
   "CHANNEL_LAYER_HOST", "String", "channel-layer", "The hostname or IP address of the server hosting the Django Channels layer (e.g., Redis or RabbitMQ)."

Authentication Options
^^^^^^^^^^^^^^^^^^^^^

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "API_AUTH_TYPE", "String", "simple_jwt", "Defines the API authentication mechanism. Valid values are ``simple_jwt``, ``keycloak``, or ``disabled`` (disables all authentication — for internal/trusted deployments only)."

**If API_AUTH_TYPE is 'keycloak', the following options are valid:**

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "OIDC_CLIENT_NAME", "String", "None", "The client ID registered with the Keycloak (OpenID Connect) server."
   "OIDC_CLIENT_SECRET", "String", "None", "The client secret for the Keycloak (OpenID Connect) client."
   "OIDC_ENDPOINT", "String", "None", "The base URL of the Keycloak (OpenID Connect) server's discovery endpoint (e.g., https://keycloak.example.com/realms/myrealm/.well-known/openid-configuration)."

**If API_AUTH_TYPE is 'simple_jwt', the following options are valid:**

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "ACCESS_TOKEN_LIFETIME", "String", "1h (1 hour)", "The duration for which access tokens are valid before expiring. Examples: 1h, 15m, 30s."
   "REFRESH_TOKEN_LIFETIME", "String", "2days (2 days)", "The duration for which refresh tokens are valid. Used to obtain new access tokens. Examples: 2days, 1w."
   "ROTATE_REFRESH_TOKENS", "Boolean", "True", "If True, a new refresh token will be issued each time a refresh token is used, invalidating the old one. Enhances security."
   "BLACKLIST_AFTER_ROTATION", "Boolean", "True", "If True, used refresh tokens are added to a blacklist, preventing their reuse after rotation."
   "SIGNING_KEY", "String", "SECRET_KEY", "The key used for signing JWT tokens. If not explicitly set, Django's SECRET_KEY will be used. **Should be a strong, unique secret.**"

Worker Container Configuration Options
--------------------------------------

These options are specifically applicable to the worker (Celery) container, which processes tasks dispatched from the API.

Celery Queue Naming
^^^^^^^^^^^^^^^^^^^

These three variables are crucial for the worker to correctly identify and connect to its designated Celery task queue. They **must match** the corresponding values used by the API's models endpoint when dispatching tasks.

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "MODEL_SUPPLIER_ID", "String", "None", "Identifier for the model supplier, forming part of the Celery queue name."
   "MODEL_ID", "String", "None", "Identifier for the specific model, forming part of the Celery queue name."
   "MODEL_VERSION_ID", "String", "None", "Identifier for the model version, forming part of the Celery queue name."

Workflow Run Mode
^^^^^^^^^^^^^^^^

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "RUN_MODE", "String", "None", "Determines the worker's operational mode. ``v1``: single-server legacy workflow. ``v2``: distributed modern workflow. ``server-internal``: internal worker mode where the worker runs inside the server container (used for lightweight single-container deployments)."

Worker Paths
^^^^^^^^^^^^

These options define file locations within the worker container for models, configuration, and run data.

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "MODEL_SETTINGS_FILE", "String", "/home/worker/model/meta-data/model_settings.json", "The absolute path to the model_settings.json meta file, containing model-specific configuration."
   "OASISLMF_CONFIG", "String", "/home/worker/model/oasislmf.json", "The absolute path to the oasislmf.json configuration file, used by the OASIS LMF library."
   "MODEL_DATA_DIRECTORY", "String", "/home/worker/model", "The absolute path to the directory containing model data."
   "BASE_RUN_DIR", "String", "/tmp/run", "The base directory where temporary run files and results are stored during task execution."
   "TASK_LOG_DIR", "String", "/var/log/oasis/tasks", "The directory where specific logs for individual tasks executed by the worker are stored."

Debug Options
^^^^^^^^^^^^

These options control various debugging behaviors and features within the worker.

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "DEBUG", "Boolean", "False", "If True, enables increased and more verbose logging for worker operations, useful for debugging."
   "DISABLE_WORKER_REG", "Boolean", "False", "If True, disables the worker's automatic self-registration process with the API server's 'models' endpoint upon connection."

V2 Mode Only Options
^^^^^^^^^^^^^^^^^^^^

These options are only relevant and applied when RUN_MODE is set to 'v2'.

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "KEEP_LOCAL_DATA", "Boolean", "False", "If True, the worker will retain local temporary data generated during task execution after the task completes."
   "KEEP_REMOTE_DATA", "Boolean", "False", "If True, the worker will retain remote data (e.g., in object storage) generated during task execution after the task completes."
   "FAIL_ON_REDELIVERY", "Boolean", "True", "A safeguard mechanism. If True, the worker checks if a task has been previously attempted. If a task has been redelivered (attempted multiple times, e.g., 3 times), it will mark the task as failed."

V1 Mode Only Options
^^^^^^^^^^^^^^^^^^^^

These options are only relevant and applied when RUN_MODE is set to 'v1'.

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "KEEP_RUN_DIR", "Boolean", "False", "If True, the temporary run directories created for tasks will not be deleted after the task completes, remaining within the container."
   "LOCK_FILE", "String", "/tmp/tmp_lock_file", "The absolute path to a lock file used to prevent multiple jobs from executing concurrently on the same machine/worker instance."
   "LOCK_TIMEOUT_IN_SECS", "Integer", "None", "The maximum time in seconds to wait for the LOCK_FILE to become available before a task gives up trying to acquire the lock."
   "LOCK_RETRY_COUNTDOWN_IN_SECS", "Integer", "None", "The time in seconds to wait before retrying to acquire the LOCK_FILE if it is currently held."

Storage Related Options
^^^^^^^^^^^^^^^^^^^^^^^

These options configure the worker's ability to interact with various storage backends for input/output data.

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "STORAGE_TYPE", "String", "shared-fs", "Defines the backend storage solution. Valid values are 'S3' (AWS S3), 'AZURE' (Azure Blob Storage), or 'shared-fs' (a common file system accessible by containers)."

**If STORAGE_TYPE is 'S3', the following options are valid:**

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "AWS_ACCESS_KEY_ID", "String", "None", "Your AWS access key ID. Required for S3 authentication."
   "AWS_SECRET_ACCESS_KEY", "String", "None", "Your AWS secret access key. Required for S3 authentication."
   "AWS_BUCKET_NAME", "String", "None", "The name of the S3 bucket where files will be stored or retrieved by the worker."
   "AWS_SHARED_BUCKET", "String", "None", "(Inferred) Specifies a shared S3 bucket name if multiple components access the same shared storage."
   "AWS_LOCATION", "String", "None", "The base path or directory within the S3 bucket where worker-related files are stored."
   "AWS_QUERYSTRING_EXPIRE", "Integer", "3600", "The expiration time in seconds for signed S3 URLs generated by the worker."
   "AWS_QUERYSTRING_AUTH", "Boolean", "True", "If True, generated URLs for S3 objects will include query string authentication."
   "AWS_LOG_LEVEL", "String", "INFO", "Logging level for AWS S3 operations performed by the worker."

**If STORAGE_TYPE is 'AZURE', the following options are valid:**

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "AZURE_ACCOUNT_NAME", "String", "None", "Your Azure Storage account name. Required for Azure Blob Storage."
   "AZURE_ACCOUNT_KEY", "String", "None", "Your Azure Storage account key. Required for Azure Blob Storage."
   "AZURE_CONTAINER", "String", "None", "The name of the Azure Blob Storage container where files will be stored or retrieved by the worker."
   "AZURE_LOCATION", "String", "None", "The base path or virtual directory within the Azure container where worker-related files are stored."
   "AZURE_SHARED_CONTAINER", "String", "None", "(Inferred) Specifies a shared Azure container name if multiple components access the same shared storage."
   "AZURE_LOG_LEVEL", "String", "INFO", "Logging level for Azure Blob Storage operations performed by the worker."
   "AZURE_SSL", "Boolean", "True", "If True, secure SSL connections will be used for Azure Blob Storage."
   "AZURE_UPLOAD_MAX_CONN", "Integer", "2", "The maximum number of concurrent connections to use for Azure Blob uploads."
   "AZURE_CONNECTION_TIMEOUT_SECS", "Integer", "20", "The timeout in seconds for Azure Blob Storage connections."
   "AZURE_URL_EXPIRATION_SECS", "Integer", "3600", "The expiration time in seconds for generated shared access signature (SAS) URLs for Azure blobs."
   "AZURE_CONNECTION_STRING", "String", "None", "A full Azure Storage connection string. Can be used as an alternative to AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY."
   "AZURE_TOKEN_CREDENTIAL", "String", "None", "(Inferred) A token credential for authentication with Azure Blob Storage, typically for OAuth/Managed Identity."
   "AZURE_CACHE_CONTROL", "String", "None", "Value for the Cache-Control header on uploaded Azure blobs."
   "AZURE_OBJECT_PARAMETERS", "JSON/String", "None", "(Inferred) Additional parameters to apply to Azure blob objects on upload, typically as a JSON string."

Celery Configuration Options
----------------------------

The following options apply to both server and worker containers, any container connected to celery. But can vary by oasis version.

Celery Broker: Image Versions 1.28.x or Older
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "OASIS_RABBIT_HOST", "String", "broker", "Hostname of the RabbitMQ broker for Celery workers."
   "OASIS_RABBIT_PORT", "Integer", "5672", "Port of the RabbitMQ broker for Celery workers."
   "OASIS_RABBIT_USER", "String", "rabbit", "Username for connecting to the RabbitMQ broker for Celery workers."
   "OASIS_RABBIT_PASS", "String", "rabbit", "Password for connecting to the RabbitMQ broker for Celery workers."

Celery Broker: Image Versions 2.3.x or Newer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "OASIS_CELERY_BROKER_URL", "String", "amqp://rabbit:rabbit@broker:5672", "Full connection URL for the Celery broker."

Celery Results DB connection Values: Applies to All Versions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "CELERY_DB_ENGINE", "String", "db+postgresql+psycopg", "Specifies the database engine for Celery's results backend."
   "CELERY_DB_HOST", "String", "celery-db", "Hostname for the database used as Celery's results backend."
   "CELERY_DB_PASS", "String", "password", "Password for accessing the database used as Celery's results backend."
   "CELERY_DB_USER", "String", "celery", "Username for accessing the database used as Celery's results backend."
   "CELERY_DB_NAME", "String", "celery", "Name of the database used as Celery's results backend."
   "CELERY_DB_PORT", "Integer", "5432", "Port for connecting to the database used as Celery's results backend."

Celery concurrency and custom arguments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The options below are aliases for celery options which control the resource usage of the worker containers.

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "OASIS_CELERY_WORKER_MAX_TASKS_PER_CHILD", "Integer", "1", "Maximum number of tasks a celery child process executes before it is replaced. See the celery config `worker_max_tasks_per_child <https://docs.celeryq.dev/en/latest/userguide/configuration.html#worker-max-tasks-per-child>`_ for more details."
   "OASIS_CELERY_WORKER_MAX_MEMORY_PER_CHILD", "Integer", "None", "Maximum amount of resident memory in kilobytes that may be consumed by a celery child process before it is restarted. Restart occurs after the task on the child process has been completed. Corresponds to the celery config option `worker_max_memory_per_child <https://docs.celeryq.dev/en/latest/userguide/configuration.html#worker-max-memory-per-child>`_."

The Following apply only to the worker images, and are not configurable from the conf.ini file

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "OASIS_CELERY_CONCURRENCY", "Integer", "Number of available cores", "Sets the concurrency argument for Celery workers. By default, it equals the number of available cores, but can be set lower to mitigate out-of-memory errors."
   "OASIS_CELERY_EXTRA_ARGS", "String", "None", "Allows passing custom Celery arguments directly into the worker's startup command. Refer to the Celery CLI documentation for available options."

Celery Broker SSL/TLS (v2.5.2+)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

From version 2.5.2, the Celery broker connection (RabbitMQ) can be secured with SSL/TLS. Use the ``amqps://`` scheme in
``OASIS_CELERY_BROKER_URL`` and set the following options:

.. csv-table::
   :header: "Option Name", "Type", "Default", "Description"
   :widths: 20, 10, 15, 55

   "OASIS_CELERY_BROKER_SSL_CA_CERTS", "String", "None", "Path to the CA certificate file (PEM format) for verifying the RabbitMQ server certificate."
   "OASIS_CELERY_BROKER_SSL_CERTFILE", "String", "None", "Path to the client certificate file (PEM format). Leave blank for server-only authentication."
   "OASIS_CELERY_BROKER_SSL_KEYFILE", "String", "None", "Path to the client private key file (PEM format). Leave blank for server-only authentication."
   "OASIS_CELERY_BROKER_MANAGEMENT_PORT", "Integer", "15671", "RabbitMQ management UI port when using SSL (default AMQPS management port)."

Example environment configuration for SSL:

.. code-block::

    OASIS_CELERY_BROKER_URL: "amqps://rabbit:rabbit@broker:5671"
    OASIS_CELERY_BROKER_SSL_CA_CERTS: "/ssl/ca_certificate.pem"
    # Optional client cert auth:
    # OASIS_CELERY_BROKER_SSL_CERTFILE: "/ssl/client_cert.pem"
    # OASIS_CELERY_BROKER_SSL_KEYFILE: "/ssl/client_key.pem"

See ``compose/rabbitmq-ssl.docker-compose.yml`` in the OasisPlatform repository for a full example deployment.
