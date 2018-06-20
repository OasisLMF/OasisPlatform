from __future__ import absolute_import

from celery.result import AsyncResult
from celery.states import SUCCESS, STARTED, FAILURE, REJECTED, REVOKED, PENDING, RECEIVED, RETRY
from ..celery import celery_app


@celery_app.task()
def poll_analysis_status(self, pk):
    from .models import Analysis

    analysis = Analysis.objects.get(pk=pk)
    res = AsyncResult(analysis.task_id)

    reschedule = True
    if res.status == SUCCESS:
        analysis.status = Analysis.status_choices.STOPPED_COMPLETED
        reschedule = False
    elif res.status == STARTED:
        analysis.status = Analysis.status_choices.STARTED
    elif res.status in [PENDING, RECEIVED, RETRY]:
        analysis.status = Analysis.status_choices.PENDING
    elif res.status in [FAILURE, REJECTED]:
        analysis.status = Analysis.status_choices.STOPPED_ERROR
        reschedule = False
    elif res.status == REVOKED:
        analysis.status = Analysis.status_choices.STOPPED_CANCELLED
        reschedule = False

    analysis.save()

    if reschedule:
        self.retry(countdown=5)
