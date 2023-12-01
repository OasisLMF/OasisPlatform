from __future__ import absolute_import

import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.server.oasisapi.settings')
celery_app_v1 = Celery('oasisapi_v1', include=['src.server.oasisapi.analyses.v1_api'])
celery_app_v1.config_from_object('django.conf:settings', namespace='CELERY_V1')
celery_app_v1.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
