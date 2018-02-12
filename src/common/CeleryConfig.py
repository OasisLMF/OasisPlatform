from os import environ

#: Celery config - ignore result?
CELERY_IGNORE_RESULT = False

#: Celery config - IP address of the server running RabbitMQ and Celery
BROKER_URL = "amqp://{RABBIT_USER}:{RABBIT_PASS}@{RABBIT_HOST}:{RABBIT_PORT}//".format(
    RABBIT_USER=environ.get('RABBIT_USER', 'guest'),
    RABBIT_PASS=environ.get('RABBIT_PASS', 'guest'),
    RABBIT_HOST=environ.get('RABBIT_HOST', 'oasis_rabbit'),
    RABBIT_PORT=environ.get('RABBIT_PORT', 5671),
)

#: Celery config - result backend URI
CELERY_RESULT_BACKEND = 'db+mysql://{CELERY_MYSQL_USER}:{CELERY_MYSQL_PASS}@{MYSQL_HOST}:{MYSQL_PORT}/celery'.format(
    CELERY_MYSQL_USER=environ.get('CELERY_MYSQL_USER', 'celery'),
    CELERY_MYSQL_PASS=environ.get('CELERY_MYSQL_PASS', 'password'),
    MYSQL_HOST=environ.get('MYSQL_HOST', 'oasis_mysql'),
    MYSQL_PORT=environ.get('MYSQL_PORT', 3306),
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
