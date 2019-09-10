from __future__ import absolute_import

import glob
import logging
import os
import shutil
import tarfile
import uuid
from contextlib import contextmanager, suppress

import fasteners
import tempfile

from celery import Celery, signature
from celery.task import task
from celery.signals import worker_ready

from oasislmf.cli.model import GenerateOasisFilesCmd, GenerateLossesCmd
from oasislmf.utils.status import OASIS_TASK_STATUS
from oasislmf.utils.exceptions import OasisException
from oasislmf.utils.log import oasis_log
from pathlib2 import Path

from ..conf import celeryconf as celery_conf
from ..conf.iniconf import settings
from ..common.data import STORED_FILENAME, ORIGINAL_FILENAME

'''
Celery task wrapper for Oasis ktools calculation.
'''

ARCHIVE_FILE_SUFFIX = '.tar'

RUNNING_TASK_STATUS = OASIS_TASK_STATUS["running"]["id"]

CELERY = Celery()
CELERY.config_from_object(celery_conf)

logging.info("Started worker")
logging.info("MODEL_DATA_DIRECTORY: {}".format(settings.get('worker', 'MODEL_DATA_DIRECTORY')))
logging.info("KTOOLS_BATCH_COUNT: {}".format(settings.get('worker', 'KTOOLS_BATCH_COUNT')))
logging.info("KTOOLS_ALLOC_RULE_GUL: {}".format(settings.get('worker', 'KTOOLS_ALLOC_RULE_GUL')))
logging.info("KTOOLS_ALLOC_RULE_IL: {}".format(settings.get('worker', 'KTOOLS_ALLOC_RULE_IL')))
logging.info("KTOOLS_MEMORY_LIMIT: {}".format(settings.get('worker', 'KTOOLS_MEMORY_LIMIT')))
logging.info("DEBUG_MODE: {}".format(settings.get('worker', 'DEBUG_MODE', fallback=False)))
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


# When a worker connects send a task to the worker-monitor to register a new model
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

    model_root = settings.get('worker', 'model_data_directory', fallback='/var/oasis/')
    model_specific_conf = Path(model_root, '{}-oasislmf.json'.format(model_id))
    if model_specific_conf.exists():
        return str(model_specific_conf)

    return str(Path(model_root, 'oasislmf.json'))


def get_unique_filename(ext):
    """Create a unique filename using a random UUID4.

    Args:
        ext (str): File extension to use.

    Returns:
        str: A random unique filename.

    """
    filename = "{}{}".format(uuid.uuid4().hex, ext)
    return filename


@task(name='run_analysis', bind=True)
def start_analysis_task(self, input_location, analysis_settings_file, complex_data_files=None):
    """Task wrapper for running an analysis.

    Args:
        self: Celery task instance.
        analysis_settings_file (str): Path to the analysis settings.
        input_location (str): Path to the input tar file.
        complex_data_files (list of complex_model_data_file): List of dicts containing
            on-disk and original filenames for required complex model data files.

    Returns:
        (string) The location of the outputs.
    """

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

            self.update_state(state=RUNNING_TASK_STATUS)
            output_location = start_analysis(
                os.path.join(settings.get('worker', 'MEDIA_ROOT'), analysis_settings_file),
                input_location,
                complex_data_files=complex_data_files
            )
        except Exception:
            logging.exception("Model execution task failed.")
            raise

        return output_location


@oasis_log()
def start_analysis(analysis_settings_file, input_location, complex_data_files=None):
    """Run an analysis.

    Args:
        analysis_settings_file (str): Path to the analysis settings.
        input_location (str): Path to the input tar file.
        complex_data_files (list of complex_model_data_file): List of dicts containing
            on-disk and original filenames for required complex model data files.

    Returns:
        (string) The location of the outputs.

    """
    # Check that the input archive exists and is valid
    logging.info("args: {}".format(str(locals())))
    media_root = settings.get('worker', 'MEDIA_ROOT')
    input_archive = os.path.join(media_root, input_location)

    if not os.path.exists(input_archive):
        raise MissingInputsException(input_archive)
    if not tarfile.is_tarfile(input_archive):
        raise InvalidInputsException(input_archive)

    model_id = settings.get('worker', 'model_id')
    config_path = get_oasislmf_config_path(model_id)

    tmp_dir = TemporaryDir(persist=settings.getboolean('worker', 'DEBUG_MODE', fallback=False))

    if complex_data_files:
        tmp_input_dir = TemporaryDir(persist=settings.getboolean('worker', 'DEBUG_MODE', fallback=False))
    else:
        tmp_input_dir = suppress()

    with tmp_dir as oasis_files_dir, tmp_dir as run_dir, tmp_input_dir as input_data_dir:
        with tarfile.open(input_archive) as f:
            f.extractall(oasis_files_dir)

        run_args = [
            '--oasis-files-path', oasis_files_dir,
            '--config', config_path,
            '--model-run-dir', run_dir,
            '--analysis-settings-file-path', analysis_settings_file,
            '--ktools-num-processes', settings.get('worker', 'KTOOLS_BATCH_COUNT'),
            '--ktools-alloc-rule-gul', settings.get('worker', 'KTOOLS_ALLOC_RULE_GUL'),
            '--ktools-alloc-rule-il', settings.get('worker', 'KTOOLS_ALLOC_RULE_IL'),
            '--ktools-fifo-relative'
        ]
        if complex_data_files:
            prepare_complex_model_file_inputs(complex_data_files, media_root, input_data_dir)
            run_args += ['--user-data-path', input_data_dir]
        if settings.getboolean('worker', 'KTOOLS_MEMORY_LIMIT'):
            run_args.append('--ktools-mem-limit')
        if settings.getboolean('worker', 'DEBUG_MODE'):
            run_args.append('--verbose')
            logging.info('run_directory: {}'.format(oasis_files_dir))
            logging.info('args_list: {}'.format(str(run_args)))

            # Filter out any args with None as its value / And remove `--model-run-dir`
            args_list = run_args + [''] if (len(run_args) % 2) else run_args
            mdk_args = [x for t in list(zip(*[iter(args_list)] * 2)) if (None not in t) and ('--model-run-dir' not in t) for x in t]
            logging.info("\nRUNNING: \noasislmf model generate-losses {}".format(
                " ".join([str(arg) for arg in mdk_args])
            ))

        GenerateLossesCmd(argv=run_args).run()
        output_location = uuid.uuid4().hex + ARCHIVE_FILE_SUFFIX
        output_directory = os.path.join(run_dir, "output")
        with tarfile.open(os.path.join(settings.get('worker', 'MEDIA_ROOT'), output_location), "w:gz") as tar:
            tar.add(output_directory, arcname="output")

    logging.info("Output location = {}".format(output_location))

    return output_location


@task(name='generate_input')
def generate_input(loc_file,
                   acc_file=None,
                   info_file=None,
                   scope_file=None,
                   settings_file=None,
                   complex_data_files=None):
    """Generates the input files for the loss calculation stage.

    This function is a thin wrapper around "oasislmf model generate-oasis-files".
    A temporary directory is created to contain the output oasis files.

    Args:
        loc_file (str): Name of the portfolio locations file.
        acc_file (str): Name of the portfolio accounts file.
        info_file (str): Name of the portfolio reinsurance info file.
        scope_file (str): Name of the portfolio reinsurance scope file.
        settings_file (str): Name of the analysis settings file.
        complex_data_files (list of complex_model_data_file): List of dicts containing
            on-disk and original filenames for required complex model data files.

    Returns:
        (tuple(str, str)) Paths to the outputs tar file and errors tar file.

    """
    logging.info("args: {}".format(str(locals())))

    media_root = settings.get('worker', 'MEDIA_ROOT')
    location_file = os.path.join(media_root, loc_file)
    accounts_file = os.path.join(media_root, acc_file) if acc_file else None
    ri_info_file = os.path.join(media_root, info_file) if info_file else None
    ri_scope_file = os.path.join(media_root, scope_file) if scope_file else None
    lookup_settings_file = os.path.join(media_root, settings_file) if settings_file else None

    model_id = settings.get('worker', 'model_id')
    config_path = get_oasislmf_config_path(model_id)

    tmp_dir = TemporaryDir(persist=settings.getboolean('worker', 'DEBUG_MODE', fallback=False))
    if complex_data_files:
        tmp_input_dir = TemporaryDir(persist=settings.getboolean('worker', 'DEBUG_MODE', fallback=False))
    else:
        tmp_input_dir = suppress()

    with tmp_dir as oasis_files_dir, tmp_input_dir as input_data_dir:
        run_args = [
            '--oasis-files-path', oasis_files_dir,
            '--config', config_path,
            '--source-exposure-file-path', location_file,
            '--source-accounts-file-path', accounts_file,
            '--ri-info-file-path', ri_info_file,
            '--ri-scope-file-path', ri_scope_file,
        ]
        if lookup_settings_file:
            run_args += ['--complex-lookup-config-file-path', lookup_settings_file]
        if complex_data_files:
            prepare_complex_model_file_inputs(complex_data_files, media_root, input_data_dir)
            run_args += ['--user-data-path', input_data_dir]
        if settings.getboolean('worker', 'WRITE_EXPOSURE_SUMMARY', fallback=True):
            run_args.append('--summarise-exposure')

        if settings.getboolean('worker', 'DEBUG_MODE', fallback=False):
            # Filter out any args with None as its value
            args_list = run_args + [''] if (len(run_args) % 2) else run_args
            mdk_args = [x for t in list(zip(*[iter(args_list)] * 2)) if None not in t for x in t]
            logging.info('run_directory: {}'.format(oasis_files_dir))
            logging.info('args_list: {}'.format(str(run_args)))
            logging.info("\nRUNNING: \noasislmf model generate-oasis-files {}".format(
                " ".join([str(arg) for arg in mdk_args])
            ))

        GenerateOasisFilesCmd(argv=run_args).run()

        # Process Generated Files
        lookup_error_fp = next(iter(glob.glob(os.path.join(oasis_files_dir, '*keys-errors*.csv'))), None)
        lookup_success_fp = next(iter(glob.glob(os.path.join(oasis_files_dir, 'gul_summary_map.csv'))), None)
        lookup_validation_fp = next(iter(glob.glob(os.path.join(oasis_files_dir, 'exposure_summary_report.json'))), None)
        summary_levels_fp = next(iter(glob.glob(os.path.join(oasis_files_dir, 'exposure_summary_levels.json'))), None)

        if lookup_error_fp:
            hashed_filename = os.path.join(media_root, '{}.csv'.format(uuid.uuid4().hex))
            shutil.copy(lookup_error_fp, hashed_filename)
            lookup_error_fp = str(Path(hashed_filename).relative_to(media_root))

        if lookup_success_fp:
            hashed_filename = os.path.join(media_root, '{}.csv'.format(uuid.uuid4().hex))
            shutil.copy(lookup_success_fp, hashed_filename)
            lookup_success_fp = str(Path(hashed_filename).relative_to(media_root))

        if lookup_validation_fp:
            hashed_filename = os.path.join(media_root, '{}.json'.format(uuid.uuid4().hex))
            shutil.copy(lookup_validation_fp, hashed_filename)
            lookup_validation_fp = str(Path(hashed_filename).relative_to(media_root))

        if summary_levels_fp:
            hashed_filename = os.path.join(media_root, '{}.json'.format(uuid.uuid4().hex))
            shutil.copy(summary_levels_fp, hashed_filename)
            summary_levels_fp = str(Path(hashed_filename).relative_to(media_root))

        output_tar_name = os.path.join(media_root, '{}.tar.gz'.format(uuid.uuid4().hex))
        output_tar_path = str(Path(output_tar_name).relative_to(media_root))

        logging.info("output_tar_fp: {}".format(output_tar_path))
        logging.info("lookup_error_fp: {}".format(lookup_error_fp))
        logging.info("lookup_success_fp: {}".format(lookup_success_fp))
        logging.info("lookup_validation_fp: {}".format(lookup_validation_fp))
        logging.info("summary_levels_fp: {}".format(summary_levels_fp))

        with tarfile.open(output_tar_name, 'w:gz') as tar:
            tar.add(oasis_files_dir, arcname='/')

        return output_tar_path, lookup_error_fp, lookup_success_fp, lookup_validation_fp, summary_levels_fp


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


def prepare_complex_model_file_inputs(complex_model_files, upload_directory, run_directory):
    """Places the specified complex model files in the run_directory.

    The unique upload filenames are converted back to the original upload names, so that the
    names match any input configuration file.

    On Linux, the files are symlinked, whereas on Windows the files are simply copied.

    Args:
        complex_model_files (list of complex_model_data_file): List of dicts giving the files
            to make available.
        upload_directory (str): Source directory containing the uploaded files with unique filenames.
        run_directory (str): Model inputs directory to place the files in.

    Returns:
        None.

    """
    for cmf in complex_model_files:
        from_path = os.path.join(upload_directory, cmf[STORED_FILENAME])
        to_path = os.path.join(run_directory, cmf[ORIGINAL_FILENAME])

        if os.name == 'nt':
            shutil.copy(from_path, to_path)
        else:
            os.symlink(from_path, to_path)
