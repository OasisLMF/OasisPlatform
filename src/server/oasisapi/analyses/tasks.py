from __future__ import absolute_import

import uuid
import os

from celery.utils.log import get_task_logger
from celery import Task
from celery import signals
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone

# Remove this
from six import StringIO

from botocore.exceptions import ClientError as S3_ClientError
from tempfile import TemporaryFile
from urllib.request import urlopen
from urllib.parse import urlparse

from src.server.oasisapi.files.models import RelatedFile
from src.server.oasisapi.files.views import handle_json_data
from src.server.oasisapi.schemas.serializers import ModelParametersSerializer

from ..celery import celery_app
logger = get_task_logger(__name__)


def is_valid_url(url):
    if url:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
    else:
        return False

def is_in_bucket(object_key):
    if not hasattr(default_storage, 'bucket'):
        return False
    else:
        try:
            default_storage.bucket.Object(object_key).load()
            return True
        except S3_ClientError as e:
            if e.response['Error']['Code'] == "404":
                return False
            else:
                raise e


def store_file(reference, content_type, creator, required=True, filename=None):
    """ Returns a `RelatedFile` obejct to store

    :param reference: Storage reference of file (url or file path)
    :type  reference: string

    :param content_type: Mime type of file
    :type  content_type: string

    :param creator: Id of Django user
    :type  creator: int

    :param required: Allow for None returns if set to false
    :type  required: boolean

    :return: Model Object holding a Django file
    :rtype RelatedFile
    """

    # Download data from URL
    if is_valid_url(reference):
        response = urlopen(reference)
        fdata = response.read()

        # Find file name
        header_fname = response.headers.get('Content-Disposition', '').split('filename=')[-1]
        ref = header_fname if header_fname else os.path.basename(urlparse(reference).path)
        fname = filename if filename else ref 
        logger.info('Store file: {}'.format(ref))

        # Create temp file, download content and store
        with TemporaryFile() as tmp_file:
            tmp_file.write(fdata)
            tmp_file.seek(0)
            return RelatedFile.objects.create(
                file=File(tmp_file, name=fname),
                filename=fname,
                content_type=content_type,
                creator=creator,
                store_as_filename=True,
            )

    # Issue S3 object Copy
    if is_in_bucket(reference):
        fname = filename if filename else ref
        new_file = ContentFile('')
        new_file.name = fname
        new_related_file = RelatedFile.objects.create(
            file=new_file,
            filename=fname,
            content_type=content_type,
            creator=creator,
            store_as_filename=True,
        )   
        stored_file = default_storage.open(new_related_file.file.name)
        stored_file.obj.copy({"Bucket": default_storage.bucket.name, "Key": reference})
        return new_related_file

    try:
        ref = str(os.path.basename(reference))
        fname = filename if filename else ref
        return RelatedFile.objects.create(
            file=ref,
            filename=fname,
            content_type=content_type,
            creator=creator,
            store_as_filename=True,
        )
    except TypeError as e:
        if not required:
            logger.warning(f'Failed to store file reference: {reference} - {e}')
            return None
        else:
            raise e


def delete_prev_output(object_model, field_list=[]):
    files_for_removal = list()

    # collect prev attached files
    for field in field_list:
        current_file = getattr(object_model, field)
        if current_file:
            logger.info('delete {}: {}'.format(field, current_file))
            setattr(object_model, field, None)
            files_for_removal.append(current_file)

    # Clear fields
    object_model.save(update_fields=field_list)

    # delete old files
    for f in files_for_removal:
        f.delete()


class LogTaskError(Task):
    # from gist https://gist.github.com/darklow/c70a8d1147f05be877c3
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        try:
            self.handle_task_failure(exc, task_id, args, kwargs, einfo)
        except Exception as e:
            logger.info('Unhandled Exception in: {}'.format(self.name))
            logger.exception(str(e))

        super(LogTaskError, self).on_failure(exc, task_id, args, kwargs, einfo)

    def handle_task_failure(self, exc, task_id, args, kwargs, traceback):
        logger.info('name: {}'.format(self.name))
        logger.info('args: {}'.format(args))
        logger.info('kwargs: {}'.format(kwargs))
        logger.info('traceback: {}'.format(traceback))
        files_for_removal = list()

        if self.name in ['record_run_analysis_result', 'record_generate_input_result']:
            _, analysis_pk, initiator_pk = args

            from .models import Analysis
            initiator = get_user_model().objects.get(pk=initiator_pk)
            analysis = Analysis.objects.get(pk=analysis_pk)
            random_filename = '{}.txt'.format(uuid.uuid4().hex)
            traceback_msg = "worker-monitor error:\n {}".format(traceback)
            analysis.task_finished = timezone.now()

            # Store status first, incase issue is in file storage
            if self.name == 'record_generate_input_result':
                analysis.status = Analysis.status_choices.INPUTS_GENERATION_ERROR
            if self.name == 'record_run_analysis_result':
                analysis.status = Analysis.status_choices.RUN_ERROR

            # Store Error to traceback file
            try:
                if self.name == 'record_generate_input_result':
                    with TemporaryFile() as tmp_file:
                        tmp_file.write(traceback_msg.encode('utf-8'))
                        analysis.input_generation_traceback_file = RelatedFile.objects.create(
                            file=File(tmp_file, name=random_filename),
                            filename=random_filename,
                            content_type='text/plain',
                            creator=initiator,
                        )

                if self.name == 'record_run_analysis_result':
                    with TemporaryFile() as tmp_file:
                        tmp_file.write(traceback_msg.encode('utf-8'))
                        analysis.run_traceback_file = RelatedFile.objects.create(
                            file=File(tmp_file, name=random_filename),
                            filename=random_filename,
                            content_type='text/plain',
                            creator=initiator,
                        )
                    delete_prev_output(analysis, ['run_log_file'])
                analysis.save()

            except Exception as e:
                # ensure error status is stored (if storage fails)
                analysis.save()
                raise e


@signals.worker_ready.connect
def log_worker_monitor(sender, **k):
    logger.info('DEBUG: {}'.format(settings.DEBUG))
    logger.info('DB_ENGINE: {}'.format(settings.DB_ENGINE))
    logger.info('STORAGE_TYPE: {}'.format(settings.STORAGE_TYPE))
    logger.info('DEFAULT_FILE_STORAGE: {}'.format(settings.DEFAULT_FILE_STORAGE))
    logger.info('MEDIA_ROOT: {}'.format(settings.MEDIA_ROOT))
    logger.info('AWS_STORAGE_BUCKET_NAME: {}'.format(settings.AWS_STORAGE_BUCKET_NAME))
    logger.info('AWS_LOCATION: {}'.format(settings.AWS_LOCATION))
    logger.info('AWS_S3_REGION_NAME: {}'.format(settings.AWS_S3_REGION_NAME))
    logger.info('AWS_QUERYSTRING_AUTH: {}'.format(settings.AWS_QUERYSTRING_AUTH))
    logger.info('AWS_QUERYSTRING_EXPIRE: {}'.format(settings.AWS_QUERYSTRING_EXPIRE))
    logger.info('AWS_SHARED_BUCKET: {}'.format(settings.AWS_SHARED_BUCKET))
    logger.info('AWS_IS_GZIPPED: {}'.format(settings.AWS_IS_GZIPPED))

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
                handle_json_data(model, 'resource_file', request, ModelParametersSerializer)
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
        analysis.task_started = timezone.now()
        analysis.save(update_fields=["status", "task_started"])
        logger.info('Task Status Update: analysis_pk: {}, status: {}, time: {}'.format(analysis_pk, task_status, analysis.task_started))
    except Exception as e:
        logger.error('Task Status Update: Failed')
        logger.exception(str(e))


@celery_app.task(name='record_run_analysis_result', base=LogTaskError)
def record_run_analysis_result(res, analysis_pk, initiator_pk):
    output_location, traceback_location, log_location, return_code = res
    logger.info('output_location: {}, log_location: {}, traceback_location: {}, status: {}, analysis_pk: {}, initiator_pk: {}'.format(
        output_location, traceback_location, log_location, return_code, analysis_pk, initiator_pk))

    from .models import Analysis
    initiator = get_user_model().objects.get(pk=initiator_pk)
    analysis = Analysis.objects.get(pk=analysis_pk)
    analysis.status = Analysis.status_choices.RUN_COMPLETED if return_code == 0 else Analysis.status_choices.RUN_ERROR
    analysis.task_finished = timezone.now()

    delete_prev_output(analysis, ['output_file', 'run_log_file', 'run_traceback_file'])

    # Store results
    if return_code == 0:
        analysis.output_file = store_file(output_location, 'application/gzip', initiator, filename=f'analysis_{analysis_pk}_output.tar.gz')
    # Store Ktools logs
    if log_location:
        analysis.run_log_file = store_file(log_location, 'application/gzip', initiator, filename=f'analysis_{analysis_pk}_logs.tar.gz')
    # record the error file
    if traceback_location:
        analysis.run_traceback_file = store_file(traceback_location, 'text/plain', initiator, filename=f'analysis_{analysis_pk}_run_traceback.txt')
    analysis.save()


@celery_app.task(name='record_generate_input_result', base=LogTaskError)
def record_generate_input_result(result, analysis_pk, initiator_pk):
    logger.info('result: {}, analysis_pk: {}, initiator_pk: {}'.format(
        result, analysis_pk, initiator_pk))

    from .models import Analysis
    (
        input_location,
        lookup_error_fp,
        lookup_success_fp,
        lookup_validation_fp,
        summary_levels_fp,
        traceback_fp,
        return_code,
    ) = result

    analysis = Analysis.objects.get(pk=analysis_pk)
    initiator = get_user_model().objects.get(pk=initiator_pk)

    # Remove previous output
    delete_prev_output(analysis, [
        'output_file',
        'input_file',
        'lookup_errors_file',
        'lookup_success_file',
        'lookup_validation_file',
        'summary_levels_file',
        'input_generation_traceback_file',
        'run_traceback_file',
        'run_log_file',
    ])

    # SUCCESS
    if return_code == 0:
        analysis.status = Analysis.status_choices.READY
    # FAILED
    else:
        analysis.status = Analysis.status_choices.INPUTS_GENERATION_ERROR

    # Add current Output
    analysis.input_file = store_file(input_location, 'application/gzip', initiator, filename=f'analysis_{analysis_pk}_inputs.tar.gz') if input_location else None
    analysis.lookup_success_file = store_file(lookup_success_fp, 'text/csv', initiator, filename=f'analysis_{analysis_pk}_gul_summary_map.csv') if lookup_success_fp else None
    analysis.lookup_errors_file = store_file(lookup_error_fp, 'text/csv', initiator, required=False, filename=f'analysis_{analysis_pk}_keys-errors.csv') if lookup_error_fp else None
    analysis.lookup_validation_file = store_file(lookup_validation_fp, 'application/json', initiator, required=False, filename=f'analysis_{analysis_pk}_exposure_summary_report.json') if lookup_validation_fp else None
    analysis.summary_levels_file = store_file(summary_levels_fp, 'application/json', initiator, required=False, filename=f'analysis_{analysis_pk}_exposure_summary_levels.json') if summary_levels_fp else None
    analysis.task_finished = timezone.now()

    # always store traceback
    if traceback_fp:
        analysis.input_generation_traceback_file = store_file(traceback_fp, 'text/plain', initiator, filename=f'analysis_{analysis_pk}_generation_traceback.txt')
        logger.info(analysis.input_generation_traceback_file)
    analysis.save()

@celery_app.task(name='record_run_analysis_failure')
def record_run_analysis_failure(analysis_pk, initiator_pk, traceback):
    logger.warning('"run_analysis_success" is deprecated and should only be used to process tasks already on the queue.')
    logger.info('analysis_pk: {}, initiator_pk: {}, traceback: {}'.format(
        analysis_pk, initiator_pk, traceback))

    try:
        from .models import Analysis

        analysis = Analysis.objects.get(pk=analysis_pk)
        analysis.status = Analysis.status_choices.RUN_ERROR
        analysis.task_finished = timezone.now()
        analysis.save()

        random_filename = '{}.txt'.format(uuid.uuid4().hex)
        with TemporaryFile() as tmp_file:
            tmp_file.write(traceback.encode('utf-8'))
            analysis.run_traceback_file = RelatedFile.objects.create(
                file=File(tmp_file, name=random_filename),
                filename=f'analysis_{analysis_pk}_run_traceback.txt',
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


@celery_app.task(name='record_generate_input_failure')
def record_generate_input_failure(analysis_pk, initiator_pk, traceback):
    logger.info('analysis_pk: {}, initiator_pk: {}, traceback: {}'.format(
        analysis_pk, initiator_pk, traceback))
    try:
        from .models import Analysis

        analysis = Analysis.objects.get(pk=analysis_pk)
        analysis.status = Analysis.status_choices.INPUTS_GENERATION_ERROR
        analysis.task_finished = timezone.now()
        analysis.save()

        random_filename = '{}.txt'.format(uuid.uuid4().hex)
        with TemporaryFile() as tmp_file:
            tmp_file.write(traceback.encode('utf-8'))
            analysis.input_generation_traceback_file = RelatedFile.objects.create(
                file=File(tmp_file, name=random_filename),
                filename=f'analysis_{analysis_pk}_generation_traceback.txt',
                content_type='text/plain',
                creator=get_user_model().objects.get(pk=initiator_pk),
            )

        analysis.save()
    except Exception as e:
        logger.exception(str(e))

## --- Deprecated tasks ---------------------------------------------------- ##

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



@celery_app.task(name='generate_input_success')
def generate_input_success(result, analysis_pk, initiator_pk):
    logger.warning('"generate_input_success" is deprecated and should only be used to process tasks already on the queue.')

    logger.info('result: {}, analysis_pk: {}, initiator_pk: {}'.format(
        result, analysis_pk, initiator_pk))
    try:
        from .models import Analysis
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

        # Delete previous error trace
        if analysis.input_generation_traceback_file:
            traceback = analysis.input_generation_traceback_file
            analysis.input_generation_traceback_file = None
            traceback.delete()

        analysis.save()
    except Exception as e:
        logger.exception(str(e))
