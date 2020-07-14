from src.conf.iniconf import settings

#: Celery config - ignore result?
CELERY_IGNORE_RESULT = False

#: Celery config - IP address of the server running RabbitMQ and Celery
BROKER_URL = "amqp://{RABBIT_USER}:{RABBIT_PASS}@{RABBIT_HOST}:{RABBIT_PORT}//".format(
    RABBIT_USER=settings.get('celery', 'rabbit_user', fallback='rabbit'),
    RABBIT_PASS=settings.get('celery', 'rabbit_pass', fallback='rabbit'),
    RABBIT_HOST=settings.get('celery', 'rabbit_host', fallback='127.0.0.1'),
    RABBIT_PORT=settings.get('celery', 'rabbit_port', fallback='5672'),
)

#: Celery config - result backend URI
CELERY_RESULTS_DB_BACKEND = settings.get('celery', 'DB_ENGINE', fallback='db+sqlite')
if CELERY_RESULTS_DB_BACKEND == 'db+sqlite':
    CELERY_RESULT_BACKEND = '{DB_ENGINE}:///{DB_NAME}'.format(
        DB_ENGINE=CELERY_RESULTS_DB_BACKEND,
        DB_NAME=settings.get('celery', 'db_name', fallback='celery.db.sqlite'),
    )
else:
    CELERY_RESULT_BACKEND = '{DB_ENGINE}://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'.format(
        DB_ENGINE=settings.get('celery', 'db_engine'),
        DB_USER=settings.get('celery', 'db_user'),
        DB_PASS=settings.get('celery', 'db_pass'),
        DB_HOST=settings.get('celery', 'db_host'),
        DB_PORT=settings.get('celery', 'db_port'),
        DB_NAME=settings.get('celery', 'db_name', fallback='celery'),
    )

#: Celery config - AMQP task result expiration time
CELERY_AMQP_TASK_RESULT_EXPIRES = 1000

#: Celery config - task serializer
CELERY_TASK_SERIALIZER = 'json'

#: Celery config - result serializer
CELERY_RESULT_SERIALIZER = 'json'

#: Celery config - accept content type
CELERY_ACCEPT_CONTENT = ['json']

#: Celery config - timezone
CELERY_TIMEZONE = 'Europe/London'

#: Celery config - enable UTC
CELERY_ENABLE_UTC = True

#: Celery config - concurrency
CELERYD_CONCURRENCY = 1
