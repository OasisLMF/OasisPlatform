from celery import Celery
from ..conf import celery as celery_conf


CELERY = Celery()
CELERY.config_from_object(celery_conf)
