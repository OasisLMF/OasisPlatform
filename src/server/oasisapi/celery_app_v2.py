from __future__ import absolute_import

import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.server.oasisapi.settings')
celery_app_v2 = Celery('oasisapi_v2', include=['src.server.oasisapi.analyses.v2_api'])
celery_app_v2.config_from_object('django.conf:settings', namespace='CELERY_V2')
celery_app_v2.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
