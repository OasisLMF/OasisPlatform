from __future__ import absolute_import

import glob
import logging
import os
import shutil
import tarfile
import uuid
from contextlib import contextmanager

import fasteners
import tempfile

from celery import Celery, signature
from celery.task import task
from celery.signals import worker_ready

from oasislmf.cli.model import GenerateOasisFilesCmd, GenerateLossesCmd
from oasislmf.utils import status
from oasislmf.utils.exceptions import OasisException
from oasislmf.utils.log import oasis_log
from pathlib2 import Path

from ..conf import celeryconf as celery_conf
from ..conf.iniconf import settings

'''
Celery task wrapper for Oasis ktools calculation.
'''

ARCHIVE_FILE_SUFFIX = '.tar'

CELERY = Celery()
CELERY.config_from_object(celery_conf)

logging.info("Started worker")
logging.info("MODEL_DATA_DIRECTORY: {}".format(settings.get('worker', 'MODEL_DATA_DIRECTORY')))
logging.info("KTOOLS_BATCH_COUNT: {}".format(settings.get('worker', 'KTOOLS_BATCH_COUNT')))
logging.info("KTOOLS_ALLOC_RULE: {}".format(settings.get('worker', 'KTOOLS_ALLOC_RULE')))
logging.info("KTOOLS_MEMORY_LIMIT: {}".format(settings.get('worker', 'KTOOLS_MEMORY_LIMIT')))
logging.info("KEEP_RUN_DIR: {}".format(settings.get('worker', 'KEEP_RUN_DIR')))
logging.info("LOCK_RETRY_COUNTDOWN_IN_SECS: {}".format(settings.get('worker', 'LOCK_RETRY_COUNTDOWN_IN_SECS')))
logging.info("MEDIA_ROOT: {}".format(settings.get('worker', 'MEDIA_ROOT')))


class TemporaryDir(object):
    """Context manager for mkdtemp() with option to persist"""

    def __init__(self, persist=False):
        self.persist = persist

    def __enter__(self):
        self.name = tempfile.mkdtemp()
        return self.name

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.persist:
            shutil.rmtree(self.name)


@worker_ready.connect
def register_worker(sender, **k):
    m_supplier = os.environ.get('OASIS_MODEL_SUPPLIER_ID')
    m_name = os.environ.get('OASIS_MODEL_ID')
    m_id = os.environ.get('OASIS_MODEL_VERSION_ID')
    logging.info('register_worker: SUPPLIER_ID={}, MODEL_ID={}, VERSION_ID={}'.format(m_supplier, m_name, m_id))
    signature(
        'run_register_worker',
        args=(m_supplier, m_name, m_id),
        queue='celery'
    ).delay()


class MissingInputsException(OasisException):
    def __init__(self, input_archive):
        super(MissingInputsException, self).__init__('Inputs location not found: {}'.format(input_archive))


class InvalidInputsException(OasisException):
    def __init__(self, input_archive):
        super(InvalidInputsException, self).__init__('Inputs location not a tarfile: {}'.format(input_archive))


class MissingModelDataException(OasisException):
    def __init__(self, model_data_path):
        super(MissingModelDataException, self).__init__('Model data not found: {}'.format(model_data_path))


@contextmanager
def get_lock():
    lock = fasteners.InterProcessLock(settings.get('worker', 'LOCK_FILE'))
    gotten = lock.acquire(blocking=False, timeout=settings.getfloat('worker', 'LOCK_TIMEOUT_IN_SECS'))
    yield gotten

    if gotten:
        lock.release()


def get_oasislmf_config_path(model_id):
    conf_var = settings.get('worker', 'oasislmf_config', fallback=None)
    if conf_var:
        return conf_var

    model_root = settings.get('worker', 'model_data_directory', fallback='/var/oasis/model_data/')
    model_specific_conf = Path(model_root, '{}-oasislmf.json'.format(model_id))
    if model_specific_conf.exists():
        return str(model_specific_conf)

    return str(Path(model_root, 'oasislmf.json'))


@task(name='run_analysis', bind=True)
def start_analysis_task(self, input_location, analysis_settings_file):
    '''
    Task wrapper for running an analysis.
    Args:
        analysis_profile_json (string): The analysis settings.
    Returns:
        (string) The location of the outputs.
    '''

    logging.info("LOCK_FILE: {}".format(settings.get('worker', 'LOCK_FILE')))
    logging.info("LOCK_RETRY_COUNTDOWN_IN_SECS: {}".format(
        settings.get('worker', 'LOCK_RETRY_COUNTDOWN_IN_SECS')))

    with get_lock() as gotten:
        if not gotten:
            logging.info("Failed to get resource lock - retry task")
            raise self.retry(
                max_retries=None,
                countdown=settings.getint('worker', 'LOCK_RETRY_COUNTDOWN_IN_SECS'))

        logging.info("Acquired resource lock")

        try:
            logging.info("MEDIA_ROOT: {}".format(settings.get('worker', 'MEDIA_ROOT')))
            logging.info("MODEL_DATA_DIRECTORY: {}".format(settings.get('worker', 'MODEL_DATA_DIRECTORY')))
            logging.info("KTOOLS_BATCH_COUNT: {}".format(settings.get('worker', 'KTOOLS_BATCH_COUNT')))
            logging.info("KTOOLS_MEMORY_LIMIT: {}".format(settings.get('worker', 'KTOOLS_MEMORY_LIMIT')))

            self.update_state(state=status.STATUS_RUNNING)
            output_location = start_analysis(
                os.path.join(settings.get('worker', 'MEDIA_ROOT'), analysis_settings_file),
                input_location
            )
        except Exception:
            logging.exception("Model execution task failed.")
            raise

        return output_location


@oasis_log()
def start_analysis(analysis_settings_file, input_location):
    '''
    Run an analysis.
    Args:
        analysis_profile_json (string): The analysis settings.
    Returns:
        (string) The location of the outputs.
    '''
    # Check that the input archive exists and is valid
    logging.info("args: {}".format(str(locals())))
    input_archive = os.path.join(settings.get('worker', 'MEDIA_ROOT'), input_location)

    if not os.path.exists(input_archive):
        raise MissingInputsException(input_archive)
    if not tarfile.is_tarfile(input_archive):
        raise InvalidInputsException(input_archive)

    model_id = settings.get('worker', 'model_id')
    config_path = get_oasislmf_config_path(model_id)

    TmpDir = TemporaryDir(settings.get('worker', 'KEEP_RUN_DIR'))
    with TmpDir as oasis_files_dir, TmpDir as run_dir:
        with tarfile.open(input_archive) as f:
            f.extractall(oasis_files_dir)

        run_args = [
            '--oasis-files-path', oasis_files_dir,
            '--config', config_path,
            '--model-run-dir', run_dir,
            '--analysis-settings-file-path', analysis_settings_file,
            '--ktools-num-processes', settings.get('worker', 'KTOOLS_BATCH_COUNT'),
            '--ktools-alloc-rule', settings.get('worker', 'KTOOLS_ALLOC_RULE'),
            '--ktools-fifo-relative'
        ]

        if settings.getboolean('worker', 'KTOOLS_MEMORY_LIMIT'):
            run_args.append('--ktools-mem-limit')

        GenerateLossesCmd(argv=run_args).run()
        output_location = uuid.uuid4().hex + ARCHIVE_FILE_SUFFIX

        output_directory = os.path.join(run_dir, "output")
        with tarfile.open(os.path.join(settings.get('worker', 'MEDIA_ROOT'), output_location), "w:gz") as tar:
            tar.add(output_directory, arcname="output")

    logging.info("Output location = {}".format(output_location))

    return output_location


@task(name='generate_input')
def generate_input(loc_file, acc_file=None, info_file=None, scope_file=None):
    logging.info("args: {}".format(str(locals())))

    media_root = settings.get('worker', 'media_root')
    location_file = os.path.join(media_root, loc_file)
    accounts_file = os.path.join(media_root, acc_file) if acc_file else None
    ri_info_file = os.path.join(media_root, info_file) if info_file else None
    ri_scope_file = os.path.join(media_root, scope_file) if scope_file else None

    model_id = settings.get('worker', 'model_id')
    config_path = get_oasislmf_config_path(model_id)

    TmpDir = TemporaryDir(settings.get('worker', 'KEEP_RUN_DIR'))
    with TmpDir as oasis_files_dir:
        run_args = [
            '--oasis-files-path', oasis_files_dir,
            '--config', config_path,
            '--source-exposure-file-path', location_file,
            '--source-accounts-file-path', accounts_file,
            '--ri-info-file-path', ri_info_file,
            '--ri-scope-file-path', ri_scope_file
        ]
        GenerateOasisFilesCmd(argv=run_args).run()

        error_path = next(iter(glob.glob(os.path.join(oasis_files_dir, '*keys-errors*.csv'))), None)
        error_path_tar = None

        if error_path:
            saved_path = os.path.join(media_root, '{}.tar.gz'.format(uuid.uuid4().hex))
            shutil.copy(error_path, saved_path)
            error_tar = str(Path(saved_path).relative_to(media_root))

        output_name = os.path.join(media_root, '{}.tar.gz'.format(uuid.uuid4().hex))
        output_tar = str(Path(output_name).relative_to(media_root))

        logging.info("output_tar: {}".format(output_tar))
        logging.info("saved_path: {}".format(saved_path))

        logging.info("error_tar: {}".format(error_tar))
        logging.info("error_tar: {}".format(error_tar))

        with tarfile.open(output_name, 'w:gz') as tar:
            tar.add(oasis_files_dir, arcname='/')

        return output_tar, error_tar


@task(name='on_error')
def on_error(request, ex, traceback, record_task_name, analysis_pk, initiator_pk):
    """
    Because of how celery works we need to include a celery task registered in the
    current app to pass to the `link_error` function on a chain.

    This function takes the error and passes it on back to the server so that it can store
    the info on the analysis.
    """
    signature(
        record_task_name,
        args=(analysis_pk, initiator_pk, traceback),
        queue='celery'
    ).delay()
