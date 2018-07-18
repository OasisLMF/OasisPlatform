from __future__ import absolute_import

import uuid

from celery.result import AsyncResult
from celery.states import SUCCESS, STARTED, FAILURE, REJECTED, REVOKED, PENDING, RECEIVED, RETRY
from celery.utils.log import get_task_logger
from django.contrib.auth import get_user_model
from django.core.files import File
from six import StringIO

from src.server.oasisapi.files.models import RelatedFile
from ..celery import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name='run_analysis_success')
def run_analysis_success(output_location, analysis_pk, initiator_pk):
    from .models import Analysis

    analysis = Analysis.objects.get(pk=analysis_pk)
    analysis.status = Analysis.status_choices.RUN_COMPLETED

    analysis.output_file = RelatedFile.objects.create(
        file=str(output_location),
        content_type='application/gzip',
        creator=get_user_model().objects.get(pk=initiator_pk),
    )

    analysis.save()


@celery_app.task(name='record_run_analysis_failure')
def record_run_analysis_failure(analysis_pk, initiator_pk, traceback):
    from .models import Analysis

    analysis = Analysis.objects.get(pk=analysis_pk)
    analysis.status = Analysis.status_choices.RUN_ERROR

    analysis.run_traceback_file = RelatedFile.objects.create(
        file=File(StringIO(traceback), name='{}.txt'.format(uuid.uuid4().hex)),
        content_type='text/plain',
        creator=get_user_model().objects.get(pk=initiator_pk),
    )

    analysis.save()


@celery_app.task(name='generate_input_success')
def generate_input_success(result, analysis_pk, initiator_pk):
    from .models import Analysis

    input_location, errors_location = result

    analysis = Analysis.objects.get(pk=analysis_pk)
    analysis.status = Analysis.status_choices.READY

    analysis.input_file = RelatedFile.objects.create(
        file=str(input_location),
        content_type='application/gzip',
        creator=get_user_model().objects.get(pk=initiator_pk),
    )

    analysis.input_errors_file = RelatedFile.objects.create(
        file=str(errors_location),
        content_type='text/csv',
        creator=get_user_model().objects.get(pk=initiator_pk),
    )

    analysis.save()


@celery_app.task(name='record_generate_input_failure')
def record_generate_input_failure(analysis_pk, initiator_pk, traceback):
    from .models import Analysis

    analysis = Analysis.objects.get(pk=analysis_pk)
    analysis.status = Analysis.status_choices.INPUTS_GENERATION_ERROR

    analysis.input_generation_traceback_file = RelatedFile.objects.create(
        file=File(StringIO(traceback), name='{}.txt'.format(uuid.uuid4().hex)),
        content_type='text/plain',
        creator=get_user_model().objects.get(pk=initiator_pk),
    )

    analysis.save()
