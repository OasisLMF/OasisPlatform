from __future__ import absolute_import

import os
from celery import Celery
from django.conf import settings
from kombu import Queue, Exchange
from ...conf.celeryconf_v2 import CELERY_QUEUE_MAX_PRIORITY


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.server.oasisapi.settings.v2')
v2 = Celery('v2', include=['src.server.oasisapi.analyses.v2_api'])
v2.config_from_object('django.conf:settings')
v2.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

#  CONFIG WARNING: 
#
#  Both Celery apps (v1 & v2) share a single 'conf' objecting when running in the HTTP server,
#  Only way to support both Old and new dispatch options is to default the `CELERY_MAX_QUEUE_PRIORITY=None`
#  then to manually set the v2 queues to priority n 
#
#  Once a V2 task hits either the "v2-worker-monitor" or "v2-task-controller" the 'src.server.oasisapi.settings.v2' settings will be active, 
#  which will load with the correct default "CELERY_MAX_QUEUE_PRIORITY=10" 
v2.conf.task_queues = [
    Queue('celery-v2', Exchange('celery-v2'), routing_key='celery-v2', queue_arguments={'x-max-priority': CELERY_QUEUE_MAX_PRIORITY}),
    Queue('task-controller', Exchange('task-controller'), routing_key='task-controller', queue_arguments={'x-max-priority': CELERY_QUEUE_MAX_PRIORITY}),
]
