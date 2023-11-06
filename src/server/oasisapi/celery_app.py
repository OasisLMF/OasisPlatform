from __future__ import absolute_import

import os
import copy

from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.server.oasisapi.settings')

celery_app = Celery('oasisapi')
celery_app.config_from_object('django.conf:settings')
celery_app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


#import ipdb; ipdb.set_trace()

celery_app_v1 = copy.deepcopy(celery_app)
celery_app_v1.conf.task_default_routing_key = 'celery'
celery_app_v1.conf['CELERY_QUEUE_MAX_PRIORITY'] = None
