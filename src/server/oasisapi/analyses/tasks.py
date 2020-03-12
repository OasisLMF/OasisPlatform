from __future__ import absolute_import

import os
import tarfile
import uuid
from datetime import datetime
from glob import glob
from itertools import chain
from shutil import rmtree

from celery.result import AsyncResult
from celery.signals import before_task_publish
from celery.utils.log import get_task_logger
from django.contrib.auth import get_user_model
from django.core.files import File
from django.db.models import When, Case, Value, F
from django.utils import timezone

# Remove this
from six import StringIO

from src.conf.iniconf import settings
from src.server.oasisapi.files.models import RelatedFile
from .models import AnalysisTaskStatus
from .task_controller import get_analysis_task_controller
from tempfile import TemporaryFile
from urllib.request import urlopen
from urllib.parse import urlparse

from ..celery import celery_app
logger = get_task_logger(__name__)


TaskId = str
PathStr = str


def is_valid_url(url):
    if url:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
    else:
        return False


def store_file(reference, content_type, creator):
    if not reference:
        return None

    if is_valid_url(reference):
        # Download to a tmp location and pass the file refrence for storage
        response = urlopen(reference)
        fdata = response.read()

        # Find file name
        header_fname = response.headers.get('Content-Disposition', '').split('filename=')[-1]
        fname = header_fname if header_fname else os.path.basename(urlparse(reference).path)
        logger.info('Store file: {}'.format(fname))

        # Store in a temp file and upload
        with TemporaryFile() as tmp_file:
            tmp_file.write(fdata)
            tmp_file.seek(0)
            return RelatedFile.objects.create(
                file=File(tmp_file, name=fname),
                filename=fname,
                content_type=content_type,
                creator=creator,
            )

    else:
        # create RelatedFile object from filepath
        file_name = os.path.basename(reference)
        file_path = os.path.join(
            settings.get('worker', 'MEDIA_ROOT'),
            file_name,
        )
        return RelatedFile.objects.create(
            file=file_path,
            filename=file_name,
            content_type=content_type,
            creator=creator,
        )


def _traceback_from_errback_args(*args):
    try:
        request, exc, tb = args
    except ValueError:
        failing_res = AsyncResult(args[0])
        tb = failing_res.traceback

    return tb


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


@celery_app.task(bind=True, name='record_input_files')
def record_input_files(self, result, analysis_id=None, initiator_id=None, slug=None):
    from .models import Analysis

    record_sub_task_start.delay(analysis_id=analysis_id, task_slug=slug, task_id=self.request.id)
    logger.info('result: {}, analysis_id: {}, initiator_id: {}'.format(
        result, analysis_id, initiator_id))

    initiator = get_user_model().objects.get(id=initiator_id)

    input_location = result.get('output_location')
    lookup_error_fp = result.get('lookup_error_location')
    lookup_success_fp = result.get('lookup_success_location')
    lookup_validation_fp = result.get('lookup_validation_location')
    summary_levels_fp = result.get('summary_levels_location')
    log_location = result.get('log_location')

    analysis = Analysis.objects.get(pk=analysis_id)
    analysis.task_finished = timezone.now()

    analysis.status = Analysis.status_choices.READY
    analysis.input_file = store_file(input_location, 'application/gzip', initiator)
    analysis.lookup_errors_file = store_file(lookup_error_fp, 'text/csv', initiator)
    analysis.lookup_success_file = store_file(lookup_success_fp, 'text/csv', initiator)
    analysis.lookup_validation_file = store_file(lookup_validation_fp, 'application/json', initiator)
    analysis.summary_levels_file = store_file(summary_levels_fp, 'application/json', initiator)

    # always store traceback
    if log_location:
        analysis.input_generation_traceback_file = store_file(log_location, 'text/plain', initiator)
        logger.info(analysis.input_generation_traceback_file)

    analysis.save()
    return result


@celery_app.task(bind=True, name='record_losses_files')
def record_losses_files(self, result, analysis_id=None, initiator_id=None, slug=None):
    from .models import Analysis

    record_sub_task_start.delay(analysis_id=analysis_id, task_slug=slug, task_id=self.request.id)

    initiator = get_user_model().objects.get(pk=initiator_id)
    analysis = Analysis.objects.get(pk=analysis_id)
    analysis.status = Analysis.status_choices.RUN_COMPLETED
    analysis.task_finished = timezone.now()

    # Trace back file (stdout + stderr)
    traceback_location = f'{uuid.uuid4().hex}.tar.gz'
    with open(os.path.join(settings.get('worker', 'MEDIA_ROOT'), traceback_location), 'w') as f:
        f.write(result['bash_trace'])

    # Ktools log Tar file
    log_location = f'{uuid.uuid4().hex}.tar.gz'
    log_directory = os.path.join(result['model_run_fp'], "log")
    if os.path.exists(log_directory):
        with tarfile.open(os.path.join(settings.get('worker', 'MEDIA_ROOT'), log_location), "w:gz") as tar:
            tar.add(log_directory, arcname="log")

        analysis.run_log_file = RelatedFile.objects.create(
            file=str(log_location),
            filename=str(log_location),
            content_type='application/gzip',
            creator=initiator,
        )

    # Results Tar
    output_location = f'{uuid.uuid4().hex}.tar.gz'
    output_directory = os.path.join(result['model_run_fp'], "output")
    if os.path.exists(output_directory):
        with tarfile.open(os.path.join(settings.get('worker', 'MEDIA_ROOT'), output_location), "w:gz") as tar:
            tar.add(output_directory, arcname="output")

        analysis.output_file = RelatedFile.objects.create(
            file=str(output_location),
            filename=str(output_location),
            content_type='application/gzip',
            creator=initiator,
        )

    analysis.save()

    return result


@celery_app.task(bind=True, name='record_sub_task_start')
def record_sub_task_start(self, analysis_id=None, task_slug=None, task_id=None):
    _now = timezone.now()

    AnalysisTaskStatus.objects.filter(
        analysis_id=analysis_id,
        slug=task_slug
    ).update(
        task_id=task_id,
        start_time=Case(
            When(
                start_time__isnull=True,
                then=Value(_now),
            ),
            default=F('start_time')
        ),
        status=Case(
            When(
                status=AnalysisTaskStatus.status_choices.QUEUED,
                then=Value(AnalysisTaskStatus.status_choices.STARTED),
            ),
            default=F('status')
        )
    )


@celery_app.task(bind=True, name='record_sub_task_success')
def record_sub_task_success(self, res, analysis_id=None, initiator_id=None, task_slug=None):
    log_location = res.get('log_location')
    error_location = res.get('error_location')

    task_id = self.request.parent_id
    AnalysisTaskStatus.objects.filter(
        slug=task_slug,
        analysis_id=analysis_id,
    ).update(
        task_id=task_id,
        status=AnalysisTaskStatus.status_choices.COMPLETED,
        end_time=timezone.now(),
        output_log=None if not log_location else RelatedFile.objects.create(
            file=str(log_location),
            filename='{}-output.log'.format(task_id),
            content_type='text/plain',
            creator_id=initiator_id,
        ),
        error_log=None if not error_location else RelatedFile.objects.create(
            file=str(error_location),
            filename='{}-error.log'.format(task_id),
            content_type='text/plain',
            creator_id=initiator_id,
        )
    )


@celery_app.task(bind=True, name='record_sub_task_failure')
def record_sub_task_failure(self, *args, analysis_id=None, initiator_id=None, task_slug=None):
    tb = _traceback_from_errback_args(*args)

    task_id = self.request.parent_id
    AnalysisTaskStatus.objects.filter(
        slug=task_slug,
        analysis_id=analysis_id,
    ).update(
        task_id=task_id,
        status=AnalysisTaskStatus.status_choices.ERROR,
        end_time=timezone.now(),
        error_log=RelatedFile.objects.create(
            file=File(StringIO(tb), name='{}.log'.format(uuid.uuid4())),
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
        status__in=unfinished_statuses,
        analysis_id=analysis_id
    ).update(
        status=AnalysisTaskStatus.status_choices.CANCELLED,
        end_time=timezone.now(),
    )


@celery_app.task(name='handle_task_failure')
def handle_task_failure(
    *args,
    analysis_id=None,
    initiator_id=None,
    run_dir_patterns=None,
    traceback_property=None,
    failure_status=None,
):
    tb = _traceback_from_errback_args(*args)

    logger.info('analysis_pk: {}, initiator_pk: {}, traceback: {}, run_dir_patterns: {}, failure_status: {}'.format(
        analysis_id, initiator_id, tb, run_dir_patterns, failure_status))
    try:
        from .models import Analysis

        analysis = Analysis.objects.get(pk=analysis_id)
        analysis.status = failure_status
        analysis.task_finished = timezone.now()

        random_filename = '{}.txt'.format(uuid.uuid4().hex)
        setattr(analysis, traceback_property, RelatedFile.objects.create(
            file=File(StringIO(tb), name=random_filename),
            filename=random_filename,
            content_type='text/plain',
            creator=get_user_model().objects.get(pk=initiator_id),
        ))

        # remove the current command log file
        if analysis.run_log_file:
            analysis.run_log_file.delete()
            analysis.run_log_file = None

        analysis.save()
    except Exception as e:
        logger.exception(str(e))

    # cleanup the temporary run files
    if not settings.getboolean('worker', 'KEEP_RUN_DIR', fallback=False):
        media_root = settings.get('worker', 'media_root')

        directories = chain(glob(os.path.join(media_root, p)) for p in run_dir_patterns)

        for p in directories:
            rmtree(p)


@before_task_publish.connect
def mark_task_as_queued_receiver(*args, headers=None, body=None, **kwargs):
    analysis_id = body[1].get('analysis_id')
    slug = body[1].get('slug')

    if analysis_id and slug:
        mark_task_as_queued(analysis_id, slug, headers['id'], timezone.now().timestamp())


@celery_app.task(name='mark_task_as_queued')
def mark_task_as_queued(analysis_id, slug, task_id, dt):
    AnalysisTaskStatus.objects.filter(
        analysis_id=analysis_id,
        slug=slug,
    ).update(
        task_id=task_id,
        status=AnalysisTaskStatus.status_choices.QUEUED,
        queue_time=datetime.fromtimestamp(dt, tz=timezone.utc),
    )
