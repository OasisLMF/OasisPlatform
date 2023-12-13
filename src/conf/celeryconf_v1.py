import urllib
from src.conf.iniconf import settings
from .base import *

# Default Queue Name
CELERY_DEFAULT_QUEUE = "celery"

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
CELERYD_CONCURRENCY = 1

#: Disable celery task prefetch
#: https://docs.celeryproject.org/en/stable/userguide/configuration.html#std-setting-worker_prefetch_multiplier
CELERYD_PREFETCH_MULTIPLIER = 1

worker_task_kwargs = {
    'autoretry_for': (Exception,),
    'max_retries': 2,               # The task will be run max_retries + 1 times
    'default_retry_delay': 6,       # A small delay to recover from temporary bad states
}
