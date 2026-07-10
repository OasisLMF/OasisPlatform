import ssl
import urllib
from src.conf.iniconf import settings

#: Celery config - IP address of the server running RabbitMQ and Celery
BROKER_URL = settings.get(
    'celery',
    'broker_url',
    fallback="amqp://{RABBIT_USER}:{RABBIT_PASS}@{RABBIT_HOST}:{RABBIT_PORT}//".format(
        RABBIT_USER=settings.get('celery', 'rabbit_user', fallback='rabbit'),
        RABBIT_PASS=settings.get('celery', 'rabbit_pass', fallback='rabbit'),
        RABBIT_HOST=settings.get('celery', 'rabbit_host', fallback='127.0.0.1'),
        RABBIT_PORT=settings.get('celery', 'rabbit_port', fallback='5672'),
    )
)

#: RabbitMQ management API port - defaults to 443 for amqps://, 15672 for amqp://
#: Configurable via OASIS_CELERY_BROKER_MANAGEMENT_PORT env var
BROKER_MANAGEMENT_PORT = int(settings.get(
    'celery',
    'broker_management_port',
    fallback='443' if BROKER_URL.startswith('amqps://') else '15672',
))

#: Celery config - SSL options when using amqps:// broker URL
if BROKER_URL.startswith('amqps://'):
    _broker_ssl_ca_certs = settings.get('celery', 'broker_ssl_ca_certs', fallback=None)
    _broker_ssl_certfile = settings.get('celery', 'broker_ssl_certfile', fallback=None)
    _broker_ssl_keyfile = settings.get('celery', 'broker_ssl_keyfile', fallback=None)
    BROKER_USE_SSL = {
        'ca_certs': _broker_ssl_ca_certs or None,
        'certfile': _broker_ssl_certfile or None,
        'keyfile': _broker_ssl_keyfile or None,
        'cert_reqs': ssl.CERT_REQUIRED if _broker_ssl_ca_certs else ssl.CERT_NONE,
    }

#: Celery config - result backend URI
CELERY_RESULTS_DB_BACKEND = settings.get('celery', 'DB_ENGINE', fallback='db+sqlite')
if CELERY_RESULTS_DB_BACKEND == 'db+sqlite':
    CELERY_RESULT_BACKEND = '{DB_ENGINE}:///{DB_NAME}'.format(
        DB_ENGINE=CELERY_RESULTS_DB_BACKEND,
        DB_NAME=settings.get('celery', 'db_name', fallback='celery.db.sqlite'),
    )
else:
    CELERY_RESULT_BACKEND = '{DB_ENGINE}://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}{SSL_MODE}'.format(
        DB_ENGINE=settings.get('celery', 'db_engine'),
        DB_USER=urllib.parse.quote(settings.get('celery', 'db_user')),
        DB_PASS=urllib.parse.quote(settings.get('celery', 'db_pass')),
        DB_HOST=settings.get('celery', 'db_host'),
        DB_PORT=settings.get('celery', 'db_port'),
        DB_NAME=settings.get('celery', 'db_name', fallback='celery'),
        SSL_MODE=settings.get('celery', 'db_ssl_mode', fallback='?sslmode=prefer'),
    )
