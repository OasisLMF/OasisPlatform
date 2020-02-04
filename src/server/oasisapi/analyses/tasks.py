from __future__ import absolute_import

import uuid

from celery.utils.log import get_task_logger
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.http import HttpRequest
from django.utils import timezone
from django_celery_results.utils import now
from six import StringIO

from src.server.oasisapi.files.models import RelatedFile
from src.server.oasisapi.files.views import handle_json_data
from src.server.oasisapi.schemas.serializers import ModelSettingsSerializer
from .models import AnalysisTaskStatus
from .task_controller import get_analysis_task_controller

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
        output_location, traceback_location, log_location, return_code, analysis_pk, initiator_pk))

    try:
        from .models import Analysis

        initiator = get_user_model().objects.get(pk=initiator_pk)
        analysis = Analysis.objects.get(pk=analysis_pk)
        analysis.status = Analysis.status_choices.RUN_COMPLETED if return_code == 0 else Analysis.status_choices.RUN_ERROR
        analysis.task_finished = timezone.now()

        if output_location:
            analysis.output_file = RelatedFile.objects.create(
                file=str(output_location),
                filename=str(output_location),
                content_type='application/gzip',
                creator=initiator,
            )

        # Store Ktools logs
        if log_location:
            analysis.run_log_file = RelatedFile.objects.create(
                file=str(log_location),
                filename=str(log_location),
                content_type='application/gzip',
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
def record_run_analysis_failure(request, exc, traceback, analysis_pk, initiator_pk):
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

        input_location = result['output_location']
        lookup_error_fp = result['lookup_error_location']
        lookup_success_fp = result['lookup_success_location']
        lookup_validation_fp = result['lookup_validation_location']
        summary_levels_fp = result['summary_levels_location']
        log_location = result['log_location']
        error_location = result['error_location']

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

        traceback_content = ''
        if log_location:
            with open(log_location, 'r') as f:
                traceback_content += f.read()

        if error_location:
            with open(error_location, 'w') as f:
                traceback_content += f.read()

        if traceback_content:
            traceback_filename = '{}.txt'.format(uuid.uuid4().hex)
            analysis.input_generation_traceback_file = RelatedFile.objects.create(
                file=File(StringIO(traceback_content), traceback_filename),
                filename=traceback_filename,
                content_type='text/plain',
                creator_id=initiator_pk,
            )

        analysis.save()
    except Exception as e:
        logger.exception(str(e))


@celery_app.task(name='record_generate_input_failure')
def record_generate_input_failure(request, exc, traceback, analysis_pk, initiator_pk):
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


@celery_app.task(name='start_input_generation_task')
def start_input_generation_task(analysis_pk, initiator_pk):
    from .models import Analysis
    analysis = Analysis.objects.get(pk=analysis_pk)
    initiator = get_user_model().objects.get(pk=initiator_pk)

    get_analysis_task_controller().generate_inputs(analysis, initiator)

    analysis.status = Analysis.status_choices.INPUTS_GENERATION_STARTED
    analysis.save()


@celery_app.task(name='start_loss_generation_task')
def start_loss_generation_task(analysis_pk, initiator_pk):
    from .models import Analysis
    analysis = Analysis.objects.get(pk=analysis_pk)
    initiator = get_user_model().objects.get(pk=initiator_pk)

    get_analysis_task_controller().generate_losses(analysis, initiator)

    analysis.status = Analysis.status_choices.RUN_STARTED
    analysis.save()


@celery_app.task(bind=True, name='record_sub_task_start')
def record_sub_task_start(self, analysis_id, task_id):
    _now = now()

    status, created = AnalysisTaskStatus.objects.get_or_create(
        task_id=task_id,
        analysis_id=analysis_id,
        defaults={
            'start_time': _now,
            'status': AnalysisTaskStatus.status_choices.STARTED
        }
    )

    if not created:
        status.start_time = _now

        # We dont want to change the state of the task if it has already finished
        if status.status == AnalysisTaskStatus.status_choices.QUEUED:
            status.status = AnalysisTaskStatus.status_choices.STARTED

        status.save()


@celery_app.task(bind=True, name='record_sub_task_success')
def record_sub_task_success(self, res, analysis_id, initiator_id):
    log_location = res['log_location']
    error_location = res['error_location']

    task_id = self.request.parent_id
    AnalysisTaskStatus.objects.filter(
        task_id=task_id,
        analysis_id=analysis_id,
    ).update(
        status=AnalysisTaskStatus.status_choices.COMPLETED,
        end_time=now(),
        output_log=RelatedFile.objects.create(
            file=str(log_location),
            filename='{}-output.log'.format(task_id),
            content_type='text/plain',
            creator_id=initiator_id,
        ),
        error_log=RelatedFile.objects.create(
            file=str(error_location),
            filename='{}-error.log'.format(task_id),
            content_type='text/plain',
            creator_id=initiator_id,
        )
    )


@celery_app.task(bind=True, name='record_sub_task_failure')
def record_sub_task_failure(self, request, exc, traceback, analysis_id, initiator_id):
    task_id = self.request.parent_id
    AnalysisTaskStatus.objects.filter(
        task_id=task_id,
        analysis_id=analysis_id,
    ).update(
        status=AnalysisTaskStatus.status_choices.ERROR,
        end_time=now(),
        error_log=RelatedFile.objects.create(
            file=File(StringIO(traceback), name='{}.log'.format(uuid.uuid4())),
            filename='{}-error.log'.format(task_id),
            content_type='text/plain',
            creator_id=initiator_id,
        )
    )


@celery_app.task(bind=True, name='chord_error_callback')
def chord_error_callback(self, analysis_id):
    unfinished_statuses = [AnalysisTaskStatus.status_choices.QUEUED, AnalysisTaskStatus.status_choices.STARTED]
    ids_to_revoke = AnalysisTaskStatus.objects.filter(
        analysis_id=analysis_id,
        status__in=unfinished_statuses,
    ).values_list('task_id', flat=True)

    celery_app.control.revoke(set(ids_to_revoke), terminate=True)

    AnalysisTaskStatus.objects.filter(
        task_id__in=ids_to_revoke,
        status__in=unfinished_statuses,
    ).update(
        status=AnalysisTaskStatus.status_choices.CANCELLED,
        end_time=now(),
    )
