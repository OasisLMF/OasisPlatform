from __future__ import absolute_import

import uuid

from celery.utils.log import get_task_logger
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.http import HttpRequest
from django.utils import timezone
from six import StringIO

from src.server.oasisapi.files.models import RelatedFile
from src.server.oasisapi.files.views import handle_json_data
from src.server.oasisapi.schemas.serializers import ModelSettingsSerializer

from ..celery import celery_app
logger = get_task_logger(__name__)


@celery_app.task(name='run_register_worker')
def run_register_worker(m_supplier, m_name, m_id, m_settings, m_version):
    logger.info('model_supplier: {}, model_name: {}, model_id: {}'.format(m_supplier, m_name, m_id))
    try:
        from django.contrib.auth.models import User
        from src.server.oasisapi.analysis_models.models import AnalysisModel

        try:
            model = AnalysisModel.objects.get(
                model_id=m_name,
                supplier_id=m_supplier,
                version_id=m_id
            )
        except ObjectDoesNotExist:
            user = User.objects.get(username='admin')
            model = AnalysisModel.objects.create(
                model_id=m_name,
                supplier_id=m_supplier,
                version_id=m_id,
                creator=user
            )
        
        # Update model settings file
        if m_settings:
            try:
                request = HttpRequest()
                request.data = {**m_settings}
                request.method = 'post'
                request.user = model.creator 
                handle_json_data(model, 'resource_file', request, ModelSettingsSerializer)
                logger.info('Updated model settings')
            except Exception as e:
                logger.info('Failed to update model settings:')
                logger.exception(str(e))

        # Update model version info
        if m_version:
            try:
                model.ver_ktools =  m_version['ktools']
                model.ver_oasislmf = m_version['oasislmf']
                model.ver_platform = m_version['platform']
                model.save()
                logger.info('Updated model versions')
            except Exception as e:
                logger.info('Failed to set model veriosns:')
                logger.exception(str(e))


    # Log unhandled execptions
    except Exception as e:
        logger.exception(str(e))
        logger.exception(model)

@celery_app.task(name='set_task_status')
def set_task_status(analysis_pk, task_status):
    try:
        from .models import Analysis
        analysis = Analysis.objects.get(pk=analysis_pk)
        analysis.status = task_status
        analysis.save()
        logger.info('Task Status Update: analysis_pk: {}, status: {}'.format(analysis_pk, task_status))
    except Exception as e:
        logger.error('Task Status Update: Failed')
        logger.exception(str(e))
    
@celery_app.task(name='run_analysis_success')
def run_analysis_success(output_location, analysis_pk, initiator_pk):
    logger.warning('"run_analysis_success" is deprecated and should only be used to process tasks already on the queue.')

    logger.info('output_location: {}, analysis_pk: {}, initiator_pk: {}'.format(
        output_location, analysis_pk, initiator_pk))

    try:
        from .models import Analysis
        analysis = Analysis.objects.get(pk=analysis_pk)
        analysis.status = Analysis.status_choices.RUN_COMPLETED
        analysis.task_finished = timezone.now()

        analysis.output_file = RelatedFile.objects.create(
            file=str(output_location),
            filename=str(output_location),
            content_type='application/gzip',
            creator=get_user_model().objects.get(pk=initiator_pk),
        )

        # Delete previous error trace
        if analysis.run_traceback_file:
            traceback = analysis.run_traceback_file
            analysis.run_traceback_file = None
            traceback.delete()

        analysis.save()
    except Exception as e:
        logger.exception(str(e))


@celery_app.task(name='record_run_analysis_result')
def record_run_analysis_result(res, analysis_pk, initiator_pk):
    output_location, log_location, traceback_location, return_code = res
    logger.info('output_location: {}, log_location: {}, traceback_location: {}, status: {}, analysis_pk: {}, initiator_pk: {}'.format(
        output_location, log_location, traceback_location, return_code, analysis_pk, initiator_pk))

    try:
        from .models import Analysis

        initiator = get_user_model().objects.get(pk=initiator_pk)
        analysis = Analysis.objects.get(pk=analysis_pk)
        analysis.status = Analysis.status_choices.RUN_COMPLETED if return_code == 0 else Analysis.status_choices.RUN_ERROR
        analysis.task_finished = timezone.now()

        analysis.output_file = RelatedFile.objects.create(
            file=str(output_location),
            filename=str(output_location),
            content_type='application/gzip',
            creator=initiator,
        )

        # record the log file
        if log_location:
            analysis.run_log_file = RelatedFile.objects.create(
                file=str(log_location),
                filename=str(log_location),
                content_type='text/plain',
                creator=initiator,
            )
        elif analysis.run_log_file:
            analysis.run_log_file.delete()
            analysis.run_log_file = None

        # record the error file
        if traceback_location:
            analysis.run_traceback_file = RelatedFile.objects.create(
                file=str(traceback_location),
                filename=str(traceback_location),
                content_type='text/plain',
                creator=initiator,
            )
        elif analysis.log_file:
            analysis.run_traceback_file.delete()
            analysis.run_traceback_file = None

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
        analysis.task_finished = timezone.now()

        random_filename = '{}.txt'.format(uuid.uuid4().hex)
        analysis.run_traceback_file = RelatedFile.objects.create(
            file=File(StringIO(traceback), name=random_filename),
            filename=random_filename,
            content_type='text/plain',
            creator=get_user_model().objects.get(pk=initiator_pk),
        )

        # remove the current command log file
        if analysis.run_log_file:
            analysis.run_log_file.delete()
            analysis.run_log_file = None

        analysis.save()
    except Exception as e:
        logger.exception(str(e))


@celery_app.task(name='generate_input_success')
def generate_input_success(result, analysis_pk, initiator_pk):
    logger.info('result: {}, analysis_pk: {}, initiator_pk: {}'.format(
        result, analysis_pk, initiator_pk))
    try:
        from .models import Analysis

        try:
            (
                input_location,
                lookup_error_fp,
                lookup_success_fp,
                lookup_validation_fp,
                summary_levels_fp,
                traceback_fp,
            ) = result
        except ValueError:
            # catches issues where currently queued tasks dont pass the traceback file
            traceback_fp = None
            (
                input_location,
                lookup_error_fp,
                lookup_success_fp,
                lookup_validation_fp,
                summary_levels_fp,
            ) = result

        analysis = Analysis.objects.get(pk=analysis_pk)
        analysis.status = Analysis.status_choices.READY
        analysis.task_finished = timezone.now()

        analysis.input_file = RelatedFile.objects.create(
            file=str(input_location),
            filename=str(input_location),
            content_type='application/gzip',
            creator=get_user_model().objects.get(pk=initiator_pk),
        )
        analysis.lookup_errors_file = RelatedFile.objects.create(
            file=str(lookup_error_fp),
            filename=str('keys-errors.csv'),
            content_type='text/csv',
            creator=get_user_model().objects.get(pk=initiator_pk),
        )
        analysis.lookup_success_file = RelatedFile.objects.create(
            file=str(lookup_success_fp),
            filename=str('gul_summary_map.csv'),
            content_type='text/csv',
            creator=get_user_model().objects.get(pk=initiator_pk),
        )
        analysis.lookup_validation_file = RelatedFile.objects.create(
            file=str(lookup_validation_fp),
            filename=str('exposure_summary_report.json'),
            content_type='application/json',
            creator=get_user_model().objects.get(pk=initiator_pk),
        )

        analysis.summary_levels_file = RelatedFile.objects.create(
            file=str(summary_levels_fp),
            filename=str('exposure_summary_levels.json'),
            content_type='application/json',
            creator=get_user_model().objects.get(pk=initiator_pk),
        )

        # Delete previous error trace and create the new one if set
        if analysis.input_generation_traceback_file:
            traceback = analysis.input_generation_traceback_file
            analysis.input_generation_traceback_file = None
            traceback.delete()

        if traceback_fp:
            analysis.input_generation_traceback_file = RelatedFile.objects.create(
                file=str(traceback_fp),
                filename=str(traceback_fp),
                content_type='text/plain',
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
        analysis.task_finished = timezone.now()

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
