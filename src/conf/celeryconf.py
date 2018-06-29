from src.conf.iniconf import settings

#: Celery config - ignore result?
CELERY_IGNORE_RESULT = False

#: Celery config - IP address of the server running RabbitMQ and Celery
BROKER_URL = "amqp://{RABBIT_USER}:{RABBIT_PASS}@{RABBIT_HOST}:{RABBIT_PORT}//".format(
    RABBIT_USER=settings.get('celery', 'RABBIT_USER'),
    RABBIT_PASS=settings.get('celery', 'RABBIT_PASS'),
    RABBIT_HOST=settings.get('celery', 'RABBIT_HOST'),
    RABBIT_PORT=settings.get('celery', 'RABBIT_PORT'),
)

#: Celery config - result backend URI
CELERY_RESULT_BACKEND = '{DB_ENGINE}://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/celery'.format(
    DB_ENGINE=settings.get('celery', 'DB_ENGINE'),
    DB_USER=settings.get('celery', 'DB_USER'),
    DB_PASS=settings.get('celery', 'DB_PASS'),
    DB_HOST=settings.get('celery', 'DB_HOST'),
    DB_PORT=settings.get('celery', 'DB_PORT'),
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
