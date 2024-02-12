from celery import Celery, Task, signature
from celery import current_app, signals
from celery.worker.request import Request as CeleryRequest
from celery.exceptions import WorkerLostError, Retry
from celery.signals import (before_task_publish, task_failure, task_revoked,
                            worker_ready)

from billiard.einfo import ExceptionWithTraceback
from celery.worker.request import state 
#tz_or_local = timezone.tz_or_local
#send_revoked = signals.task_revoked.send
#send_retry = signals.task_retry.send

task_accepted = state.task_accepted
task_ready = state.task_ready
revoked_tasks = state.revoked
revoked_stamps = state.revoked_stamps

from celery.exceptions import (Ignore, InvalidTaskError, Reject, Retry, TaskRevokedError, Terminated,
                               TimeLimitExceeded, WorkerLostError)


import logging 
logger = logging.getLogger(__name__)

class CustomRequest(CeleryRequest):
    """ Using 'reject_on_worker_lost=True' to re-queue a task on `WorkerLostError` results
        in an infinite loop if the task OOM errors each try.

        so instead this overrides 'on_failure' to call the standard `on_retry` call like if an
        exception occurs

        src: https://docs.celeryq.dev/en/stable/_modules/celery/worker/request.html#Request
    """
    
    ## Orig function from celery docs 
    def on_failure(self, exc_info, send_failed_event=True, return_ok=False):
        """Handler called if the task raised an exception."""

        # Logging 
        #from celery.contrib import rdb; rdb.set_trace()
        logger.info(' ---------------------------------------- ')
        logger.info(f'Name: {self.task.__name__}')
        logger.info(f'Retries: {self.task.request.retries}')
        logger.info(f'Retry max: {self.task.max_retries}')
        logger.info(f'reject_on_worker_lost: {self.task.reject_on_worker_lost}')

        
        if not self.task.max_retries:
            self.task.reject_on_worker_lost = True
        else:    
            if self.task.request.retries <= self.task.max_retries:
                self.task.request.retries += 1
                self.task.reject_on_worker_lost = True
            else:
                self.task.reject_on_worker_lost = False

        #self.task.reject_on_worker_lost
        super().on_failure(exc_info, send_failed_event, return_ok)

        #task_ready(self)
        #exc = exc_info.exception


        #if isinstance(exc, ExceptionWithTraceback):
        #    exc = exc.exc

        #is_terminated = isinstance(exc, Terminated)
        #if is_terminated:
        #    # If the task was terminated and the task was not cancelled due
        #    # to a connection loss, it is revoked.

        #    # We always cancel the tasks inside the master process.
        #    # If the request was cancelled, it was not revoked and there's
        #    # nothing to be done.
        #    # According to the comment below, we need to check if the task
        #    # is already revoked and if it wasn't, we should announce that
        #    # it was.
        #    if not self._already_cancelled and not self._already_revoked:
        #        # This is a special case where the process
        #        # would not have had time to write the result.
        #        self._announce_revoked(
        #            'terminated', True, str(exc), False)
        #    return
        #elif isinstance(exc, MemoryError):
        #    raise MemoryError(f'Process got: {exc}')
        #elif isinstance(exc, Reject):
        #    return self.reject(requeue=exc.requeue)
        #elif isinstance(exc, Ignore):
        #    return self.acknowledge()
        #elif isinstance(exc, Retry):
        #    return self.on_retry(exc_info)

        ## (acks_late) acknowledge after result stored.
        #requeue = False
        #is_worker_lost = isinstance(exc, WorkerLostError)
        #if self.task.acks_late:
        #    reject = (
        #        reject_on_worker_lost and
        #        is_worker_lost
        #    )
        #    ack = self.task.acks_on_failure_or_timeout
        #    if reject:
        #        requeue = True
        #        self.reject(requeue=requeue)
        #        send_failed_event = False
        #    elif ack:
        #        self.acknowledge()
        #    else:
        #        # supporting the behaviour where a task failed and
        #        # need to be removed from prefetched local queue
        #        self.reject(requeue=False)

        ## This is a special case where the process would not have had time
        ## to write the result.
        #if not requeue and (is_worker_lost or not return_ok):
        #    # only mark as failure if task has not been requeued
        #    self.task.backend.mark_as_failure(
        #        self.id, exc, request=self._context,
        #        store_result=self.store_errors,
        #    )

        #    signals.task_failure.send(sender=self.task, task_id=self.id,
        #                              exception=exc, args=self.args,
        #                              kwargs=self.kwargs,
        #                              traceback=exc_info.traceback,
        #                              einfo=exc_info)

        #if send_failed_event:
        #    self.send_event(
        #        'task-failed',
        #        exception=safe_repr(get_pickled_exception(exc_info.exception)),
        #        traceback=exc_info.traceback,
        #    )

        #if not return_ok:
        #    error('Task handler raised error: %r', exc,
        #          exc_info=exc_info.exc_info)






    #def on_failure(self, exc_info, send_failed_event=True, return_ok=False):
    #    self.task.max_retries = 1
    #    exc = exc_info.exception
    #    if isinstance(exc, ExceptionWithTraceback):
    #        #from celery.contrib import rdb; rdb.set_trace()
    #        if isinstance(exc.exc, WorkerLostError):
    #            self.task.retry()
    #            #exc.exc = Retry(message='worker lost')

    #    super().on_failure(exc_info, send_failed_event, return_ok)  # Call the base class method
    #    #from celery.contrib import rdb; rdb.set_trace()

    #    ##from celery.contrib import rdb; rdb.set_trace()
    #    #if isinstance(exc, WorkerLostError):
    #    #    if self.task.max_retries == 0:
    #    #        pass
    #    #    if not self.task.max_retries:
    #    #        self.task.max_retries = 3
    #    #        self.retry()
    #    #    else:
    #    #        self.task.max_retries -= 1
    #    #        self.retry()

    #    #if isinstance(exc, ExceptionWithTraceback):
    #    #    return None

    #    ##from celery.contrib import rdb; rdb.set_trace()

    #    ##if isinstance(exc, ExceptionWithTraceback):
    #    ##    exc = exc.exc

    #    ##raise self.task.retry(max_retries=3, exc=Retry(message='worker lost'))
    #    ##if isinstance(exc, WorkerLostError):
    #    ##    pass
    #    ##    #exc_info.exception = exc
    #    ##    #return self.on_retry(exc_info)
    #    ##    ###return self.retry(exc=exc)


    #    #from celery.contrib import rdb; rdb.set_trace()

# Monkey patch
#celery.worker.request.Request = CustomErrorHandler

class FailureWorkerRetry(Task):
    Request = CustomRequest

    #def on_failure(self, exc, task_id, args, kwargs, einfo):
    #    from celery.contrib import rdb; rdb.set_trace()
    #    logging.info('Celery task failure!!!1', exc_info=exc)
    #    super().on_failure(exc, task_id, args, kwargs, einfo)
