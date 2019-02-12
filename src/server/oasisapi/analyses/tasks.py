from __future__ import absolute_import

import uuid

from celery.utils.log import get_task_logger
from django.contrib.auth import get_user_model
from django.core.files import File
from six import StringIO

from src.server.oasisapi.files.models import RelatedFile

from src.server.oasisapi.analysis_models.models import AnalysisModel
from django.contrib.auth.models import User

from ..celery import celery_app

logger = get_task_logger(__name__)

@celery_app.task(name='register_worker')
def run_add_worker(m_supplier, m_name, m_id):
    logger.info('model_supplier: {}, model_name: {}, model_id: {}'.format(m_supplier, m_name, m_id))
    try:
        # fetch admin user and create new model
        user = User.objects.get(username='admin')
        new_model = AnalysisModel.objects.create(model_id=m_name, 
                                                 supplier_id=m_supplier, 
                                                 version_id=m_id, 
                                                 creator=user)
    except Exception as e:
        logger.exception(str(e))


@celery_app.task(name='run_analysis_success')
def run_analysis_success(output_location, analysis_pk, initiator_pk):
    logger.info('output_location: {}, analysis_pk: {}, initiator_pk: {}'.format(
                 output_location, analysis_pk, initiator_pk))
        
    try:    
        from .models import Analysis

        analysis = Analysis.objects.get(pk=analysis_pk)
        analysis.status = Analysis.status_choices.RUN_COMPLETED

        analysis.output_file = RelatedFile.objects.create(
            file=str(output_location),
            filename=str(output_location),
            content_type='application/gzip',
            creator=get_user_model().objects.get(pk=initiator_pk),
        )

        analysis.save()
    except Exception as e:
        logger.exception(str(e))
        

@celery_app.task(name='record_run_analysis_failure')
def record_run_analysis_failure(analysis_pk, initiator_pk, traceback):
    logger.info('analysis_pk: {}, initiator_pk: {}, traceback: {}'.format(
                 analysis_pk, initiator_pk, traceback))

    try:
        from .models import Analysis

        analysis = Analysis.objects.get(pk=analysis_pk)
        analysis.status = Analysis.status_choices.RUN_ERROR

        random_filename = '{}.txt'.format(uuid.uuid4().hex)
        analysis.run_traceback_file = RelatedFile.objects.create(
            file=File(StringIO(traceback), name=random_filename),
            filename=random_filename,
            content_type='text/plain',
            creator=get_user_model().objects.get(pk=initiator_pk),
        )

        analysis.save()
    except Exception as e:
        logger.exception(str(e))


@celery_app.task(name='generate_input_success')
def generate_input_success(result, analysis_pk, initiator_pk):
    logger.info('result: {}, analysis_pk: {}, initiator_pk: {}'.format(
                 result, analysis_pk, initiator_pk))
    try:

        from .models import Analysis
        input_location, errors_location = result

        analysis = Analysis.objects.get(pk=analysis_pk)
        analysis.status = Analysis.status_choices.READY

        analysis.input_file = RelatedFile.objects.create(
            file=str(input_location),
            filename=str(input_location),
            content_type='application/gzip',
            creator=get_user_model().objects.get(pk=initiator_pk),
        )

        analysis.input_errors_file = RelatedFile.objects.create(
            file=str(errors_location),
            filename=str(errors_location),
            content_type='text/csv',
            creator=get_user_model().objects.get(pk=initiator_pk),
        )

        analysis.save()
    except Exception as e:
        logger.exception(str(e))
    

@celery_app.task(name='record_generate_input_failure')
def record_generate_input_failure(analysis_pk, initiator_pk, traceback):
    logger.info('analysis_pk: {}, initiator_pk: {}, traceback: {}'.format(
                 analysis_pk, initiator_pk, traceback))
    try:
        from .models import Analysis

        analysis = Analysis.objects.get(pk=analysis_pk)
        analysis.status = Analysis.status_choices.INPUTS_GENERATION_ERROR

        random_filename = '{}.txt'.format(uuid.uuid4().hex)
        analysis.input_generation_traceback_file = RelatedFile.objects.create(
            file=File(StringIO(traceback), name=random_filename),
            filename=random_filename,
            content_type='text/plain',
            creator=get_user_model().objects.get(pk=initiator_pk),
        )

        analysis.save()
    except Exception as e:
        logger.exception(str(e))
