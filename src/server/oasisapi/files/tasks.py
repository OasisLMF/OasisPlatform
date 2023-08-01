from __future__ import absolute_import

from celery.utils.log import get_task_logger

from ..celery_app import celery_app
from ....conf import celeryconf as celery_conf

logger = get_task_logger(__name__)


@celery_app.task(name='run_file_conversion', **celery_conf.worker_task_kwargs)
def run_file_conversion(file_id, mapping_file):
