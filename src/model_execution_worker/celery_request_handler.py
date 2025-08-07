import logging
from celery import Task, signature
from celery.worker.request import Request as CeleryRequest
from celery.exceptions import WorkerLostError

from billiard.einfo import ExceptionWithTraceback
logger = logging.getLogger(__name__)


class CustomRequest(CeleryRequest):
    """ Using 'reject_on_worker_lost=True' to re-queue a task on `WorkerLostError` results
        in an infinite loop if the task OOM errors each try.

        so instead this overrides 'on_failure' to call the standard `on_retry` call like if an
        exception occurs

        src: https://docs.celeryq.dev/en/stable/_modules/celery/worker/request.html#Request
    """

    def on_failure(self, exc_info, send_failed_event=True, return_ok=False):
        """Handler called if the task raised an exception."""
        exc = exc_info.exception

        if isinstance(exc, ExceptionWithTraceback):
            exc = exc.exc

        is_worker_lost = isinstance(exc, WorkerLostError)
        is_retry = self.task.max_retries is not None

        if is_worker_lost and is_retry:
            logger.debug(' --- on_failure handler ---')
            logger.debug(f'Name: {self.task.__name__}')
            logger.debug(f'Retries: {self.task.request.retries}')
            logger.debug(f'Retry max: {self.task.max_retries}')
            logger.debug(f'reject_on_worker_lost: {self.task.reject_on_worker_lost}')
            if self.task.request.retries <= self.task.max_retries:
                self.task.request.retries += 1
                self.task.reject_on_worker_lost = True
            else:
                self.task.reject_on_worker_lost = False

        # report retry attempt
        try:
            task_args = self.kwargs
            task_id = self.task_id
            task_slug = task_args.get('slug')
            initiator_id = task_args.get('initiator_id')
            analysis_id = task_args.get('analysis_id')

            if analysis_id and task_slug:
                signature('subtask_retry_log').delay(
                    analysis_id,
                    initiator_id,
                    task_slug,
                    task_id,
                    exc_info.traceback,
                )
        except Exception as e:
            logger.error(f'Falied to store retry attempt logs: {exc_info}')
            logger.exception(e)

        super().on_failure(exc_info, send_failed_event, return_ok)


class WorkerLostRetry(Task):
    Request = CustomRequest


class RejectLostWorkerRequest(CeleryRequest):
    def on_failure(self, exc_info, send_failed_event=True, return_ok=False):
        self.task.reject_on_worker_lost = True
        logger.error(f"Worker lost on task {self.task.__name__}")
        logger.error(f"Error type {exc_info.type}")
        logger.debug(f"Error trace {exc_info.traceback}")
        logger.info(self.task)
        super().on_failure(exc_info, send_failed_event, return_ok)


class WorkerLostReject(Task):
    Request = RejectLostWorkerRequest
