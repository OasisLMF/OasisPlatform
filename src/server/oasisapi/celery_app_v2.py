from __future__ import absolute_import

import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.server.oasisapi.settings.v2')
v2 = Celery('v2', include=['src.server.oasisapi.analyses.v2_api'])
v2.config_from_object('django.conf:settings')
v2.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
#print(v2._conf)
