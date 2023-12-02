from celery.schedules import crontab
from kombu.common import Broadcast

from src.conf.iniconf import settings
from .base import *  

# Default Queue Name
CELERY_DEFAULT_QUEUE = "celery-v2"

#: Celery config - ignore result?
CELERY_IGNORE_RESULT = False

#: Celery config - AMQP task result expiration time
CELERY_AMQP_TASK_RESULT_EXPIRES = 1000

#: Celery config - task serializer
CELERY_TASK_SERIALIZER = 'json'

#: Celery config - result serializer
CELERY_RESULT_SERIALIZER = 'json'

#: Celery config - accept content type
CELERY_ACCEPT_CONTENT = ['json']

#: Celery config - timezone (default == UTC)
# CELERY_TIMEZONE = 'Europe/London'

#: Celery config - enable UTC
CELERY_ENABLE_UTC = True

#: Celery config - concurrency
# CELERYD_CONCURRENCY = 1

#: Disable celery task prefetch
CELERYD_PREFETCH_MULTIPLIER = 1

# setup queues so that tasks aren't removed from the queue until
# complete and reschedule if the task worker goes offline
CELERY_ACKS_LATE = True
CELERY_REJECT_ON_WORKER_LOST = True
CELERY_TASK_QUEUES = (Broadcast('model-worker-broadcast'), )

# Highest priority available
CELERY_QUEUE_MAX_PRIORITY = 10

# Set to make internal and subtasks inherit priority
CELERY_INHERIT_PARENT_PRIORITY = True

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

CELERYBEAT_SCHEDULE = {
    'send_queue_status_digest': {
        'task': 'send_queue_status_digest',
        'schedule': crontab_from_string(settings.get('celery', 'queue_status_digest_schedule', fallback='* * * * *')),
    }
}

worker_task_kwargs = {
    'autoretry_for': (Exception,),
    'max_retries': 2,               # The task will be run max_retries + 1 times
    'default_retry_delay': 6,       # A small delay to recover from temporary bad states
}
