from celery.schedules import crontab
from kombu.common import Broadcast

from src.conf.iniconf import settings

#: Celery config - ignore result?
CELERY_IGNORE_RESULT = False

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
CELERY_BROKER_URL = BROKER_URL

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

# setup queues so that tasks aren't removed from the queue until
# complete and reschedule if the task worker goes offline
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True


# setup the beat schedule
def crontab_from_string(s):
    minute, hour, day_of_week, day_of_month, month_of_year = s.split(' ')
    return crontab(
        minute=minute,
        hour=hour,
        day_of_week=day_of_week,
        day_of_month=day_of_month,
        month_of_year=month_of_year,
    )

CELERY_TASK_QUEUES = (Broadcast('model-worker-broadcast'), )

CELERYBEAT_SCHEDULE = {
    'send_queue_status_digest': {
        'task': 'send_queue_status_digest',
        'schedule': crontab_from_string(settings.get('celery', 'queue_status_digest_schedule', fallback='* * * * *')),
    }
}
