import logging
from celery import Task, signature
from celery.exceptions import WorkerLostError, MaxRetriesExceededError, Terminated

from .oasis_subprocess_runner import is_cancelled, raise_if_cancelled
from .utils import (
    notify_api_status_v1,
    notify_api_status_v2,
    notify_subtask_status_v2,
)

logger = logging.getLogger(__name__)


class OasisWorkerTask(Task):

    def __call__(self, *args, **kwargs):
        """ Make sure a cancelled task ends with `Terminated` (ignored by the error
        callbacks) instead of reporting success or a retryable failure.

        On threads/gevent/eventlet workers a revoke can't stop the task itself, only
        the oasislmf subprocess (see `oasis_subprocess_runner`), so the task can still finish or fail.
        """
        task_id = self.request.id
        try:
            result = super().__call__(*args, **kwargs)
        except Terminated:
            raise
        except Exception as exc:
            if is_cancelled(task_id):
                raise Terminated(f'Task {task_id} cancelled') from exc
            raise
        raise_if_cancelled(task_id)
        return result

    def retry(self, *args, **kwargs):
        # `autoretry_for=(Exception,)` would otherwise requeue a cancelled task
        raise_if_cancelled(self.request.id)
        return super().retry(*args, **kwargs)

    def before_start(self, task_id, args, kwargs):
        """ Only supported in celery v5.2 and above
        https://docs.celeryq.dev/en/latest/_modules/celery/app/task.html

        At the start of each task, before its run( .. ) is executed, check if its been redelivered
        meaning the executing work died unexpectedly
        """

        if 'V1_task_logger' in self.__qualname__:
            # V1 task
            analysis_id = args[0]
            initiator_id = None
            slug = None
        else:
            # V2 task
            analysis_id = kwargs.get('analysis_id', None)
            initiator_id = kwargs.get('initiator_id', None)
            slug = kwargs.get('slug', None)

        if analysis_id:
            self.task_redelivered_guard(analysis_id, initiator_id, slug)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """ (only run if task is V2)
        sub-tasks in V2 workflows record the traceback on each failed run,
        this task send the traceback details to the worker-monitor for storage.
        """
        if not 'V1_task_logger' in self.__qualname__:
            analysis_id = kwargs.get('analysis_id', None)
            initiator_id = kwargs.get('initiator_id', None)
            task_slug = kwargs.get('slug', None)

            if analysis_id and initiator_id and task_slug:
                signature('subtask_retry_log').delay(
                    analysis_id,
                    initiator_id,
                    task_slug,
                    task_id,
                    einfo.traceback,
                )

    def task_redelivered_guard(self, analysis_id, initiator_id, slug):
        redelivered = self.request.delivery_info.get('redelivered')
        state = self.AsyncResult(self.request.id).state

        # Debugging info
        logger.debug('--- check_task_redelivered ---')
        logger.debug(f'task: {slug}')
        logger.debug(f"redelivered: {redelivered}")
        logger.debug(f"state: {state}")

        logger.debug(f"default_retry_delay: {self.default_retry_delay}")
        logger.debug(f"max_retries: {self.max_retries}")
        logger.debug(f"retries: {self.request.retries}")

        # check and invoke retry if
        try:
            if redelivered:
                logger.info('WARNING: task requeue detected - triggering a retry')
                self.update_state(state='RETRY')
                self.retry(
                    exc=WorkerLostError('Task requeue detected - A worker container crashed while executing this task')
                )

        except MaxRetriesExceededError:
            logger.error('ERROR: task requeued max times - aborting task')
            if slug:
                notify_subtask_status_v2(
                    analysis_id=analysis_id,
                    initiator_id=initiator_id,
                    task_slug=slug,
                    subtask_status='ERROR',
                    error_msg='Task revoked, possible out of memory error or cancellation'
                )
                notify_api_status_v2(analysis_id, self._get_analyses_error_status())

            else:
                notify_api_status_v1(analysis_id, self._get_analyses_error_status())
            self.app.control.revoke(self.request.id, terminate=True)

    def _get_analyses_error_status(self):
        # V2 tasks
        if 'keys_generation_task' in self.__qualname__:
            return 'INPUTS_GENERATION_ERROR'
        if 'loss_generation_task' in self.__qualname__:
            return 'RUN_ERROR'

        # V1 tasks
        if self.name == 'generate_input':
            return 'INPUTS_GENERATION_ERROR'
        if self.name == 'run_analysis':
            return 'RUN_ERROR'
