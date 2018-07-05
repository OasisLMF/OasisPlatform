from __future__ import absolute_import

from celery.result import AsyncResult
from celery.states import SUCCESS, STARTED, FAILURE, REJECTED, REVOKED, PENDING, RECEIVED, RETRY
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from pathlib2 import Path

from src.server.oasisapi.files.models import RelatedFile
from ..celery import celery_app


@celery_app.task(bind=True)
def poll_analysis_run_status(self, pk, initiator_pk):
    from .models import Analysis

    analysis = Analysis.objects.get(pk=pk)
    res = AsyncResult(analysis.run_task_id)

    reschedule = True
    if res.status == SUCCESS:
        analysis.status = Analysis.status_choices.STOPPED_COMPLETED

        output_location = res.result

        analysis.output_file = RelatedFile.objects.create(
            file=str(output_location),
            content_type='application/gzip',
            creator=get_user_model().objects.get(pk=initiator_pk),
        )

        analysis.save()
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


@celery_app.task(bind=True)
def poll_analysis_input_generation_status(self, pk, initiator_pk):
    from .models import Analysis

    analysis = Analysis.objects.get(pk=pk)
    res = AsyncResult(analysis.generate_inputs_task_id)

    reschedule = True
    if res.status == SUCCESS:
        analysis.status = Analysis.status_choices.READY

        input_location = res.result

        analysis.input_file = RelatedFile.objects.create(
            file=str(input_location),
            content_type='application/gzip',
            creator=get_user_model().objects.get(pk=initiator_pk),
        )

        analysis.save()
        reschedule = False
    elif res.status in [FAILURE, REJECTED]:
        analysis.status = Analysis.status_choices.INPUTS_GENERATION_ERROR
        reschedule = False
    elif res.status == REVOKED:
        analysis.status = Analysis.status_choices.INPUTS_GENERATION_CANCELED
        reschedule = False

    analysis.save()

    if reschedule:
        self.retry(countdown=5)
