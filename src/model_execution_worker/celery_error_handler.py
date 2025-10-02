import logging
from celery import Task, signature
#from celery.worker.request import Request as CeleryRequest
from celery.exceptions import WorkerLostError



from .utils import notify_api_status, notify_subtask_status



from billiard.einfo import ExceptionWithTraceback
logger = logging.getLogger(__name__)








#class CustomRequest(CeleryRequest):
#    """ Using 'reject_on_worker_lost=True' to re-queue a task on `WorkerLostError` results
#        in an infinite loop if the task OOM errors each try.
#
#        so instead this overrides 'on_failure' to call the standard `on_retry` call like if an
#        exception occurs
#
#        src: https://docs.celeryq.dev/en/stable/_modules/celery/worker/request.html#Request
#    """
#
#
#
#
#    #def before_start(self, task_id, args, kwargs):
#    def execute_using_pool(self, pool, loglevel, logfile):
#        # call task_redelivered_guard here?
#        from celery.contrib import rdb; rdb.set_trace()
#
#
#    def on_failure(self, exc_info, send_failed_event=True, return_ok=False):
#        """Handler called if the task raised an exception."""
#        from celery.contrib import rdb; rdb.set_trace()
#        exc = exc_info.exception
#
#        if isinstance(exc, ExceptionWithTraceback):
#            exc = exc.exc
#
#        is_worker_lost = isinstance(exc, WorkerLostError)
#        is_retry = self.task.max_retries is not None
#
#        if is_worker_lost and is_retry:
#            logger.debug(' --- on_failure handler ---')
#            logger.debug(f'Name: {self.task.__name__}')
#            logger.debug(f'Retries: {self.task.request.retries}')
#            logger.debug(f'Retry max: {self.task.max_retries}')
#            logger.debug(f'reject_on_worker_lost: {self.task.reject_on_worker_lost}')
#            if self.task.request.retries <= self.task.max_retries:
#                self.task.request.retries += 1
#                self.task.reject_on_worker_lost = True
#            else:
#                self.task.reject_on_worker_lost = False
#
#        # report retry attempt
#        try:
#            task_args = self.kwargs
#            task_id = self.task_id
#            task_slug = task_args.get('slug')
#            initiator_id = task_args.get('initiator_id')
#            analysis_id = task_args.get('analysis_id')
#
#            if analysis_id and task_slug:
#                signature('subtask_retry_log').delay(
#                    analysis_id,
#                    initiator_id,
#                    task_slug,
#                    task_id,
#                    exc_info.traceback,
#                )
#        except Exception as e:
#            logger.error(f'Falied to store retry attempt logs: {exc_info}')
#            logger.exception(e)
#
#        super().on_failure(exc_info, send_failed_event, return_ok)






#def task_redelivered_guard(self, task, analysis_id, initiator_id, task_slug, error_state):
#    """ Safe guard to check if task has been attempted on worker
#    and was redelivered.

#    If 'OASIS_FAIL_ON_REDELIVERED=True' attempt the task 3 times
#    then give up and mark it as failed. This is to prevent a worker
#    crashing with OOM repeatedly failing on the same sub-task
#    """
#    if FAIL_ON_REDELIVERY:
#        redelivered = task.request.delivery_info.get('redelivered')
#        state = task.AsyncResult(task.request.id).state
#        logger.debug('--- check_task_redelivered ---')
#        logger.debug(f'task: {task_slug}')
#        logger.debug(f"redelivered: {redelivered}")
#        logger.debug(f"state: {state}")

#        if state == 'REVOKED':
#            logger.error('ERROR: task requeued three times or cancelled - aborting task')
#            notify_subtask_status(
#                analysis_id=analysis_id,
#                initiator_id=initiator_id,
#                task_slug=task_slug,
#                subtask_status='ERROR',
#                error_msg='Task revoked, possible out of memory error or cancellation'
#            )
#            notify_api_status(analysis_id, error_state)
#            task.app.control.revoke(task.request.id, terminate=True)
#            return
#        if state == 'RETRY':
#            logger.info('WARNING: task requeue detected - retry 2')
#            task.update_state(state='REVOKED')
#            return
#        if redelivered:
#            logger.info('WARNING: task requeue detected - retry 1')
#            task.update_state(state='RETRY')
#            return




class OasisWorkerTask(Task):
    #Request = CustomRequest


    def before_start(self, task_id, args, kwargs):
        """ Only supported in celery v5.2 and above
        https://docs.celeryq.dev/en/latest/_modules/celery/app/task.html
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


    def on_failure(self, exc, task_id, args, kwargs, einfo):
        try:
            self.task_failure_handler(exc, task_id, args, kwargs, einfo)
        except Exception as e:
            logger.info('Unhandled Exception in: {}'.format(self.name))
            logger.exception(str(e))
        super(OasisWorkerTask, self).on_failure(exc, task_id, args, kwargs, einfo)



    def task_failure_handler(self, exc, task_id, args, kwargs, traceback):
        #from celery.contrib import rdb; rdb.set_trace()



        if 'V1_task_logger' in self.__qualname__:
            pass


        else:
            #from celery.contrib import rdb; rdb.set_trace()
            analysis_id = kwargs.get('analysis_id', None)
            initiator_id = kwargs.get('initiator_id', None)
            task_slug = kwargs.get('slug', None)

            if analysis_id and initiator_id and task_slug:
                signature('subtask_retry_log').delay(
                    analysis_id,
                    initiator_id,
                    task_slug,
                    task_id,
                    exc_info.traceback,
                )


    def task_redelivered_guard(self, analysis_id, initiator_id, slug):

        # check and invoke retry if 
        redelivered = self.request.delivery_info.get('redelivered')
        if redelivered:
            logger.info('WARNING: task requeue detected - triggering a retry')
            self.update_state(state='RETRY')
            self.retry()
            return



        # Debugging info 
        state = self.AsyncResult(self.request.id).state
        logger.info('--- check_task_redelivered ---')
        logger.info(f'task: {slug}')
        logger.info(f"redelivered: {redelivered}")
        logger.info(f"state: {state}")

        logger.info(f"default_retry_delay: {self.default_retry_delay}")
        logger.info(f"max_retries: {self.max_retries}")
        logger.info(f"retries: {self.request.retries}")




        # Kill task 
        if self.request.retries >= self.max_retries:
            #from celery.contrib import rdb; rdb.set_trace()
            logger.error('ERROR: task requeued max times - aborting task')
            if slug:
                notify_subtask_status(
                    analysis_id=analysis_id,
                    initiator_id=initiator_id,
                    task_slug=slug,
                    subtask_status='ERROR',
                    error_msg='Task revoked, possible out of memory error or cancellation'
                )

            notify_api_status(analysis_id, self.__get_analyses_error_status())
            self.app.control.revoke(self.request.id, terminate=True)


    def __get_analyses_error_status(self):

        # V2 tasks
        if 'keys_generation_task' in self.__qualname__:
            return 'INPUTS_GENERATION_ERROR'
        if 'loss_generation_task' in self.__qualname__:
            return 'RUN_ERROR'

        # V1 tasks
        if self.name is 'generate_input':
            return 'INPUTS_GENERATION_ERROR'
        if self.name is 'run_analysis':
            return 'RUN_ERROR'
