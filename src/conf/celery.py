from .settings import settings

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
CELERY_RESULT_BACKEND = 'db+mysql+pymysql://{MYSQL_USER}:{MYSQL_PASS}@{MYSQL_HOST}:{MYSQL_PORT}/celery'.format(
    MYSQL_USER=settings.get('celery', 'MYSQL_USER'),
    MYSQL_PASS=settings.get('celery', 'MYSQL_PASS'),
    MYSQL_HOST=settings.get('celery', 'MYSQL_HOST'),
    MYSQL_PORT=settings.get('celery', 'MYSQL_PORT'),
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
