"""
Django settings for oasisapi project.

Generated by 'django-admin startproject' using Django 2.0.5.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

import os
import sys
import ssl

from django.core.exceptions import ImproperlyConfigured
from rest_framework.reverse import reverse_lazy

from ...common.shared import set_aws_log_level
from ...conf import iniconf  # noqa
from ...conf.celeryconf import *  # noqa
from ...common.shared import set_aws_log_level, set_azure_log_level


IN_TEST = 'test' in sys.argv

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

IS_UNITTEST = sys.argv[0].endswith('pytest')
IS_TESTSERVER = len(sys.argv) >= 2 and sys.argv[1] == 'runserver'

if IS_UNITTEST or IS_TESTSERVER:
    # Always set Debug mode when in dev environment
    MEDIA_ROOT = './shared-fs/'
    DEBUG = True
    DEBUG_TOOLBAR = True
    URL_SUB_PATH = False
    CONSOLE_DEBUG = True  # disable celery / db checks in health check
else:
    # SECURITY WARNING: don't run with debug turned on in production!
    MEDIA_ROOT = iniconf.settings.get('server', 'media_root', fallback=os.path.join(BASE_DIR, 'media'))
    DEBUG = iniconf.settings.getboolean('server', 'debug', fallback=False)
    DEBUG_TOOLBAR = iniconf.settings.getboolean('server', 'debug_toolbar', fallback=False)
    URL_SUB_PATH = iniconf.settings.getboolean('server', 'URL_SUB_PATH', fallback=True)
    CONSOLE_DEBUG = False

# Django 3.2 - the default pri-key field changed to 'BigAutoField.',
# https://docs.djangoproject.com/en/3.2/releases/3.2/#customizing-type-of-auto-created-primary-keys
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Remove the memory size limit
# This is to prevent 'Exception Value: Request body exceeded settings.DATA_UPLOAD_MAX_MEMORY_SIZE.'
# when uploading large Exposure files to the API
# https://docs.djangoproject.com/en/4.0/ref/settings/#data-upload-max-memory-size
DATA_UPLOAD_MAX_MEMORY_SIZE = None

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = iniconf.settings.get('server', 'secret_key', fallback='' if not DEBUG else 'supersecret')

_allowed_hosts = iniconf.settings.get('server', 'allowed_hosts', fallback='')
if _allowed_hosts:
    ALLOWED_HOSTS = _allowed_hosts.split(',')
else:
    ALLOWED_HOSTS = []

# Application definition


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_extensions',
    'django_filters',
    'rest_framework',
    'drf_yasg',
    'channels',
    'storages',

    'src.server.oasisapi.oidc',
    'src.server.oasisapi.files',
    'src.server.oasisapi.portfolios',
    'src.server.oasisapi.analyses',
    'src.server.oasisapi.analysis_models',
    'src.server.oasisapi.data_files',
    'src.server.oasisapi.healthcheck',
    'src.server.oasisapi.info',
    'src.server.oasisapi.queues',
    'django_cleanup.apps.CleanupConfig',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
]

if DEBUG:
    MIDDLEWARE.append('request_logging.middleware.LoggingMiddleware')

if DEBUG_TOOLBAR:
    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')


ROOT_URLCONF = 'src.server.oasisapi.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Database

DB_ENGINE = iniconf.settings.get('server', 'db_engine', fallback='django.db.backends.sqlite3')

if DB_ENGINE == 'django.db.backends.sqlite3':
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': os.path.join(BASE_DIR, iniconf.settings.get('server', 'db_name', fallback='db.sqlite3')),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': iniconf.settings.get('server', 'db_name'),
            'HOST': iniconf.settings.get('server', 'db_host'),
            'PORT': iniconf.settings.get('server', 'db_port'),
            'USER': iniconf.settings.get('server', 'db_user'),
            'PASSWORD': iniconf.settings.get('server', 'db_pass'),
        }
    }

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'src.server.oasisapi.filters.Backend',
    ),
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%S.%fZ',
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
}

# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

AUTHENTICATION_BACKENDS = iniconf.settings.get('server', 'auth_backends', fallback='django.contrib.auth.backends.ModelBackend').split(',')
AUTH_PASSWORD_VALIDATORS = []

API_AUTH_TYPE = iniconf.settings.get('server', 'API_AUTH_TYPE', fallback='')

if API_AUTH_TYPE == 'keycloak':

    INSTALLED_APPS += (
        'mozilla_django_oidc',
    )
    AUTHENTICATION_BACKENDS = ('src.server.oasisapi.oidc.keycloak_auth.KeycloakOIDCAuthenticationBackend',)
    REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] += ('mozilla_django_oidc.contrib.drf.OIDCAuthentication',)

    OIDC_RP_CLIENT_ID = iniconf.settings.get('server', 'OIDC_CLIENT_NAME', fallback='')
    OIDC_RP_CLIENT_SECRET = iniconf.settings.get('server', 'OIDC_CLIENT_SECRET', fallback='')
    KEYCLOAK_OIDC_BASE_URL = iniconf.settings.get('server', 'OIDC_ENDPOINT', fallback='')

    OIDC_OP_AUTHORIZATION_ENDPOINT = KEYCLOAK_OIDC_BASE_URL + 'auth'
    OIDC_OP_TOKEN_ENDPOINT = KEYCLOAK_OIDC_BASE_URL + 'token'
    OIDC_OP_USER_ENDPOINT = KEYCLOAK_OIDC_BASE_URL + 'userinfo'

    # No need to verify our internal self signed keycloak certificate
    OIDC_VERIFY_SSL = False

    SWAGGER_SETTINGS = {
        'USE_SESSION_AUTH': False,
        'SECURITY_DEFINITIONS': {
            "keycloak": {
                "type": "oauth2",
                "authorizationUrl": KEYCLOAK_OIDC_BASE_URL + 'auth',
                "refreshUrl": OIDC_OP_TOKEN_ENDPOINT + 'auth',
                "flow": "implicit",
                "scopes": {}
            }
        },
        "schemes": ["http", "https"]
    }
else:
    INSTALLED_APPS += ('rest_framework_simplejwt.token_blacklist',)
    REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] += ('rest_framework_simplejwt.authentication.JWTAuthentication',)

    # https://github.com/davesque/django-rest-framework-simplejwt
    SIMPLE_JWT = {
        'ACCESS_TOKEN_LIFETIME': iniconf.settings.get_timedelta('server', 'TOKEN_ACCESS_LIFETIME', fallback='hours=1'),
        'REFRESH_TOKEN_LIFETIME': iniconf.settings.get_timedelta('server', 'TOKEN_REFRESH_LIFETIME', fallback='days=2'),
        'ROTATE_REFRESH_TOKENS': iniconf.settings.getboolean('server', 'TOKEN_REFRESH_ROTATE', fallback=True),
        'BLACKLIST_AFTER_ROTATION': iniconf.settings.getboolean('server', 'TOKEN_REFRESH_ROTATE', fallback=True),
        'SIGNING_KEY': iniconf.settings.get('server', 'token_sigining_key', fallback=SECRET_KEY),
    }

    SWAGGER_SETTINGS = {
        'DEFAULT_INFO': 'src.server.oasisapi.urls.api_info',
        'LOGIN_URL': reverse_lazy('rest_framework:login'),
        'LOGOUT_URL': reverse_lazy('rest_framework:logout'),
        "schemes": ["http", "https"]
    }


# Make swagger aware of the protocol used by the client (web browser -> ingress)
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/
#
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Place the app in a sub path (swagger still available in /)
# FORCE_SCRIPT_NAME = '/api/'

# limit analyses logs access to admin accounts                                                                      
RESTRICT_SYSTEM_LOGS = iniconf.settings.getboolean('server', 'RESTRICT_SYSTEM_LOGS', fallback=False)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/
MEDIA_URL = '/api/media/'
STATIC_URL = '/api/static/'
STATIC_DEBUG_URL = '/static/'  # when running
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html
# Authenticate with S3
AWS_ACCESS_KEY_ID = iniconf.settings.get('server', 'AWS_ACCESS_KEY_ID', fallback=None)
AWS_SECRET_ACCESS_KEY = iniconf.settings.get('server', 'AWS_SECRET_ACCESS_KEY', fallback=None)
AWS_STORAGE_BUCKET_NAME = iniconf.settings.get('server', 'AWS_BUCKET_NAME', fallback='')

# S3 Configuration options .
AWS_DEFAULT_ACL = iniconf.settings.get('server', 'AWS_DEFAULT_ACL', fallback=None)
AWS_S3_CUSTOM_DOMAIN = iniconf.settings.get('server', 'AWS_S3_CUSTOM_DOMAIN', fallback=None)
AWS_S3_ENDPOINT_URL = iniconf.settings.get('server', 'AWS_S3_ENDPOINT_URL', fallback=None)
AWS_LOCATION = iniconf.settings.get('server', 'AWS_LOCATION', fallback='')
AWS_S3_REGION_NAME = iniconf.settings.get('server', 'AWS_S3_REGION_NAME', fallback=None)
AWS_LOG_LEVEL = iniconf.settings.get('server', 'aws_log_level', fallback="")

# Presigned generated URLs for private buckets
AWS_QUERYSTRING_AUTH = iniconf.settings.getboolean('server', 'AWS_QUERYSTRING_AUTH', fallback=False)
AWS_QUERYSTRING_EXPIRE = iniconf.settings.get('server', 'AWS_QUERYSTRING_EXPIRE', fallback=604800)

# When 'True' return the bucket object key instead of URL, this assumes a shared bucket between workers and server
AWS_SHARED_BUCKET = iniconf.settings.getboolean('server', 'AWS_SHARED_BUCKET', fallback=False)

# General optimization for faster delivery
AWS_IS_GZIPPED = True
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}


# Required Blob storage settings
# https://stackoverflow.com/questions/54729137/django-azure-upload-file-to-blob-storage/54767932
"""
AZURE_ACCOUNT_NAME = '<azure storage account name>'
AZURE_ACCOUNT_KEY = '<azure storage account key for this container>'
AZURE_CONTAINER = '<blob container name>'
AZURE_LOCATION = '<subdir in blob container name>'
"""
AZURE_ACCOUNT_NAME = iniconf.settings.get('server', 'AZURE_ACCOUNT_NAME', fallback=None)
AZURE_ACCOUNT_KEY = iniconf.settings.get('server', 'AZURE_ACCOUNT_KEY', fallback=None)
AZURE_CUSTOM_DOMAIN = f'{AZURE_ACCOUNT_NAME}.blob.core.windows.net'
AZURE_CONTAINER = iniconf.settings.get('server', 'AZURE_CONTAINER', fallback=None)
AZURE_LOCATION = iniconf.settings.get('server', 'AZURE_LOCATION', fallback='')
AZURE_SHARED_CONTAINER = iniconf.settings.get('server', 'AZURE_SHARED_CONTAINER', fallback=True)
AZURE_OVERWRITE_FILES = iniconf.settings.get('server', 'AZURE_OVERWRITE_FILES', fallback=True)

# Optional Blob storage settings
AZURE_LOG_LEVEL = iniconf.settings.get('server', 'AZURE_LOG_LEVEL', fallback="")
AZURE_SSL = iniconf.settings.get('server', 'AZURE_SSL', fallback=True)

# WARNING, adding default settings with 'None' casues storage adapter to break
# AZURE_UPLOAD_MAX_CONN = iniconf.settings.get('server', 'AZURE_UPLOAD_MAX_CONN', fallback=2)
# AZURE_CONNECTION_TIMEOUT_SECS = iniconf.settings.get('server', 'AZURE_CONNECTION_TIMEOUT_SECS', fallback=20)
# AZURE_BLOB_MAX_MEMORY_SIZE = iniconf.settings.get('server', 'AZURE_BLOB_MAX_MEMORY_SIZE', fallback='2MB')
# AZURE_URL_EXPIRATION_SECS = iniconf.settings.get('server', 'AZURE_URL_EXPIRATION_SECS', fallback=None)
# AZURE_CONNECTION_STRING = iniconf.settings.get('server', 'AZURE_CONNECTION_STRING', fallback=None)
# AZURE_TOKEN_CREDENTIAL = iniconf.settings.get('server', 'AZURE_TOKEN_CREDENTIAL', fallback=None)
# AZURE_CACHE_CONTROL = iniconf.settings.get('server', 'AZURE_CACHE_CONTROL', fallback=None)
# AZURE_OBJECT_PARAMETERS = iniconf.settings.get('server', 'AZURE_OBJECT_PARAMETERS', fallback=None)


# Select Data Storage
STORAGE_TYPE = iniconf.settings.get('server', 'storage_type', fallback="").lower()
LOCAL_FS = ['local-fs', 'shared-fs']
AWS_S3 = ['aws-s3', 's3', 'aws']
AZURE = ['azure']

if STORAGE_TYPE in LOCAL_FS:
    # Set Storage to shared volumn mount
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

elif STORAGE_TYPE in AWS_S3:
    # AWS S3 Object Store via `Django-Storages`
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    set_aws_log_level(AWS_LOG_LEVEL)

elif STORAGE_TYPE in AZURE:
    DEFAULT_FILE_STORAGE = 'storages.backends.azure_storage.AzureStorage'
    set_azure_log_level(AZURE_LOG_LEVEL)

else:
    raise ImproperlyConfigured('Invalid value for STORAGE_TYPE: {}'.format(STORAGE_TYPE))

# storage selector for exposure files
PORTFOLIO_PARQUET_STORAGE = iniconf.settings.getboolean('server', 'PORTFOLIO_PARQUET_STORAGE', fallback=False)
PORTFOLIO_UPLOAD_VALIDATION = iniconf.settings.getboolean('server', 'PORTFOLIO_UPLOAD_VALIDATION', fallback=False)
PORTFOLIO_VALIDATION_CONFIG = [
    {'name': 'required_fields', 'on_error': 'return'},
    {'name': 'unknown_column', 'on_error': 'return'},
    {'name': 'valid_values', 'on_error': 'return'},
    {'name': 'perils', 'on_error': 'return'},
    {'name': 'occupancy_code', 'on_error': 'return'},
    {'name': 'construction_code', 'on_error': 'return'},
    {'name': 'country_and_area_code', 'on_error': 'return'},
]


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'root': {
        'level': 'DEBUG',
        'handlers': ['console'],
    },
    'loggers': {
        'drf_yasg': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'numexpr': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
}
if DEBUG:
    LOGGING['loggers']['django.request'] = {
        'handlers': ['console'],
        'level': 'DEBUG',  # change debug level as appropiate
        'propagate': False,
    }


if IN_TEST:
    BROKER_URL = 'memory://'
    LOGGING['root'] = {}


CHANNEL_LAYER_SSL = iniconf.settings.getboolean('server', 'channel_layer_ssl', fallback=False)
CHANNEL_LAYER_HOST = iniconf.settings.get('server', 'channel_layer_host', fallback='localhost')
CHANNEL_LAYER_PASS = iniconf.settings.get('server', 'channel_layer_pass', fallback='')
CHANNEL_LAYER_USER = iniconf.settings.get('server', 'channel_layer_user', fallback='')
CHANNEL_LAYER_PORT = iniconf.settings.get('server', 'channel_layer_port', fallback='6379')
# CHANNEL_LAYER_PORT = iniconf.settings.get('server', 'channel_layer_port', fallback='6379' if not CHANNEL_LAYER_SSL else '6380')

if CHANNEL_LAYER_SSL:
    ssl_context = ssl.SSLContext()
    ssl_context.check_hostname = False
    channel_host = [{
        'address': f'rediss://{CHANNEL_LAYER_USER}:{CHANNEL_LAYER_PASS}@{CHANNEL_LAYER_HOST}:{CHANNEL_LAYER_PORT}/0',
        'ssl': ssl_context,
    }]
else:
    channel_host = [f'redis://{CHANNEL_LAYER_USER}:{CHANNEL_LAYER_PASS}@{CHANNEL_LAYER_HOST}:{CHANNEL_LAYER_PORT}/0']


CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': channel_host,
            'symmetric_encryption_keys': [SECRET_KEY],
            "capacity": 1500,
        },
    },
}

if IN_TEST:
    BROKER_URL = 'memory://'
    LOGGING['root'] = {}
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }


CELERY_TASK_ALWAYS_EAGER = True

if DEBUG_TOOLBAR:
    INTERNAL_IPS = [
        '127.0.0.1',
    ]

ASGI_APPLICATION = "src.server.oasisapi.routing.application"
WSGI_APPLICATION = 'src.server.oasisapi.wsgi.application'

# worker around for fixing unittesting
# in testing django.urls.resolve ignores 'FORCE_SCRIPT_NAME' but reverse returns the prefix
# causing tests url test to fail
# https://code.djangoproject.com/ticket/31724
if 'pytest' in sys.argv[0]:
    FORCE_SCRIPT_NAME = ''
    MEDIA_ROOT = './shared-fs/'

"""
Workaround, By default Django will try a chmod at file store to match its permistions, for disks
mounted as root, world writable. `drwxrwxrwx   2 root root    0 Jun  6 13:19 shared-fs`

The write content part works, but fails at chmod with:
    Exception Type: PermissionError at /V1/portfolios/3/location_file/
    Exception Value: [Errno 1] Operation not permitted: '/shared-fs/81987e7e62244184ba80a61dda2c194e.parquet'
    Request information:

To override this, that step will be skipped if 'FILE_UPLOAD_PERMISSIONS' is set as none
https://github.com/django/django/blob/main/django/core/files/storage.py#L337-L338
"""
FILE_UPLOAD_PERMISSIONS = None
