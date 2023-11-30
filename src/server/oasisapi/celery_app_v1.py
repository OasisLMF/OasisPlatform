from __future__ import absolute_import

import os
#import copy

from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.server.oasisapi.settings_v1')
#os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.server.oasisapi.settings')

celery_app_v1 = Celery('oasisapi_v1', include=['src.server.oasisapi.analyses.v1_api'])
celery_app_v1.config_from_object('django.conf:settings')
#celery_app_v1.config_from_object('django.conf:settings')
celery_app_v1.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# override queue pri & routing
#celery_app_v1 = copy.deepcopy(celery_conf)
#celery_app_v1.conf.task_default_routing_key = 'celery'
#celery_app_v1.conf.task_default_queue = 'celery'
#celery_app_v1.conf['CELERY_QUEUE_MAX_PRIORITY'] = None
