from celery.utils.log import get_task_logger

from src.server.oasisapi.celery_app_v2 import v2 as celery_app_v2

logger = get_task_logger(__name__)


@celery_app_v2.task(name='run_external_location_file', bind=True)
def run_external_location_file_task(self, job_id: str, initiator_id: int) -> None:
    from .services import run_location_file
    run_location_file(job_id, initiator_id)


@celery_app_v2.task(name='run_external_enrich', bind=True)
def run_external_enrich_task(self, job_id: str, initiator_id: int) -> None:
    from .services import run_enrich
    run_enrich(job_id, initiator_id)
