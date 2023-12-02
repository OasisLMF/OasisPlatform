from __future__ import absolute_import

import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.server.oasisapi.settings.v1')
v1 = Celery('v1', include=['src.server.oasisapi.analyses.v1_api'])
v1.config_from_object('django.conf:settings')
v1.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
#print(v1._conf)
