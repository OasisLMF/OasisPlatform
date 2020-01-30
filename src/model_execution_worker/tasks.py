from __future__ import absolute_import

import glob
import json
import logging
import os
import shutil
import subprocess
import tarfile
import uuid
import subprocess

import fasteners
import tempfile

from contextlib import contextmanager, suppress

from celery import Celery, signature
from celery.task import task
from celery.signals import worker_ready
from oasislmf.utils import status
from oasislmf.utils.exceptions import OasisException
from oasislmf.utils.log import oasis_log
from oasislmf.utils.status import OASIS_TASK_STATUS
from oasislmf import __version__ as mdk_version
from pathlib2 import Path

from ..conf import celeryconf as celery_conf
from ..conf.iniconf import settings
from ..common.data import STORED_FILENAME, ORIGINAL_FILENAME

'''
Celery task wrapper for Oasis ktools calculation.
'''

LOG_FILE_SUFFIX = '.txt'
ARCHIVE_FILE_SUFFIX = '.tar'
RUNNING_TASK_STATUS = OASIS_TASK_STATUS["running"]["id"]
CELERY = Celery()
CELERY.config_from_object(celery_conf)
logging.info("Started worker")

## Required ENV
logging.info("LOCK_FILE: {}".format(settings.get('worker', 'LOCK_FILE')))
logging.info("LOCK_TIMEOUT_IN_SECS: {}".format(settings.getfloat('worker', 'LOCK_TIMEOUT_IN_SECS')))
logging.info("LOCK_RETRY_COUNTDOWN_IN_SECS: {}".format(settings.get('worker', 'LOCK_RETRY_COUNTDOWN_IN_SECS')))
logging.info("MEDIA_ROOT: {}".format(settings.get('worker', 'MEDIA_ROOT')))

## Optional ENV
logging.info("MODEL_DATA_DIRECTORY: {}".format(settings.get('worker', 'MODEL_DATA_DIRECTORY', fallback='/var/oasis/')))
logging.info("MODEL_SETTINGS_FILE: {}".format(settings.get('worker', 'MODEL_SETTINGS_FILE', fallback=None)))
logging.info("OASISLMF_CONFIG: {}".format( settings.get('worker', 'oasislmf_config', fallback=None)))
logging.info("KTOOLS_NUM_PROCESSES: {}".format(settings.get('worker', 'KTOOLS_NUM_PROCESSES', fallback=None)))
logging.info("KTOOLS_ALLOC_RULE_GUL: {}".format(settings.get('worker', 'KTOOLS_ALLOC_RULE_GUL', fallback=None)))
logging.info("KTOOLS_ALLOC_RULE_IL: {}".format(settings.get('worker', 'KTOOLS_ALLOC_RULE_IL', fallback=None)))
logging.info("KTOOLS_ALLOC_RULE_RI: {}".format(settings.get('worker', 'KTOOLS_ALLOC_RULE_RI', fallback=None)))
logging.info("KTOOLS_ERROR_GUARD: {}".format(settings.get('worker', 'KTOOLS_ERROR_GUARD', fallback=True)))
logging.info("DEBUG_MODE: {}".format(settings.get('worker', 'DEBUG_MODE', fallback=False)))
logging.info("KEEP_RUN_DIR: {}".format(settings.get('worker', 'KEEP_RUN_DIR', fallback=False)))
logging.info("DISABLE_EXPOSURE_SUMMARY: {}".format(settings.get('worker', 'DISABLE_EXPOSURE_SUMMARY', fallback=False)))


class TemporaryDir(object):
    """Context manager for mkdtemp() with option to persist"""

    def __init__(self, persist=False):
        self.persist = persist

    def __enter__(self):
        self.name = tempfile.mkdtemp()
        return self.name

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.persist and os.path.isdir(self.name):
            shutil.rmtree(self.name)

def get_model_settings():
    """ Read the settings file from the path OASIS_MODEL_SETTINGS
        returning the contents as a python dict (none if not found)
    """
    settings_data = None
    settings_fp = settings.get('worker', 'MODEL_SETTINGS_FILE', fallback=None)
    try:
        if os.path.isfile(settings_fp):
            with open(settings_fp) as f:
                settings_data = json.load(f)
    except Exception as e:
        logging.error("Failed to load Model settings: {}".format(e))

    return settings_data



def get_worker_versions():
    """ Search and return the versions of Oasis components
    """
    ktool_ver_str = subprocess.getoutput('fmcalc -v')
    plat_ver_file = '/home/worker/VERSION'

    if os.path.isfile(plat_ver_file):
        with open(plat_ver_file, 'r') as f:
            plat_ver_str = f.read().strip()
    else:
        plat_ver_str = ""

    return {
        "oasislmf": mdk_version,
        "ktools": ktool_ver_str,
        "platform": plat_ver_str
    }


# When a worker connects send a task to the worker-monitor to register a new model
@worker_ready.connect
def register_worker(sender, **k):
    m_supplier = os.environ.get('OASIS_MODEL_SUPPLIER_ID')
    m_name = os.environ.get('OASIS_MODEL_ID')
    m_id = os.environ.get('OASIS_MODEL_VERSION_ID')
    m_settings = get_model_settings()
    m_version = get_worker_versions()
    logging.info('register_worker: SUPPLIER_ID={}, MODEL_ID={}, VERSION_ID={}'.format(m_supplier, m_name, m_id))
    logging.info('versions: {}'.format(m_version))
    logging.info('settings: {}'.format(m_settings))
    signature(
        'run_register_worker',
        args=(m_supplier, m_name, m_id, m_settings, m_version),
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


# Send notification back to the API Once task is read from Queue
def notify_api_task_started(analysis_pk, task_id):
    logging.info("Notify API tasks has started: analysis_id={}, task_id={}".format(
        analysis_pk,
        task_id
    ))
    signature(
        'record_sub_task_start',
        args=(analysis_pk, task_id),
        queue='celery'
    ).delay()


@task(name='run_analysis', bind=True)
def start_analysis_task(self, analysis_pk, input_location, analysis_settings_file, complex_data_files=None):
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
            notify_api_task_started(analysis_pk, self.request.id)
            self.update_state(state=RUNNING_TASK_STATUS)
            output_location, log_location, error_location, return_code = start_analysis(
                os.path.join(settings.get('worker', 'MEDIA_ROOT'), analysis_settings_file),
                input_location,
                complex_data_files=complex_data_files
            )
        except Exception:
            logging.exception("Model execution task failed.")
            raise

        return {
            'output_location': output_location,
            'log_location': log_location,
            'error_location': error_location,
            'return_code': return_code,
        }


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
    logging.info(str(get_worker_versions()))

    media_root = settings.get('worker', 'MEDIA_ROOT')
    input_archive = os.path.join(media_root, input_location)

    if not os.path.exists(input_archive):
        raise MissingInputsException(input_archive)
    if not tarfile.is_tarfile(input_archive):
        raise InvalidInputsException(input_archive)

    model_id = settings.get('worker', 'model_id')
    config_path = get_oasislmf_config_path(model_id)

    tmp_dir = TemporaryDir(persist=settings.getboolean('worker', 'KEEP_RUN_DIR', fallback=False))

    if complex_data_files:
        tmp_input_dir = TemporaryDir(persist=settings.getboolean('worker', 'KEEP_RUN_DIR', fallback=False))
    else:
        tmp_input_dir = suppress()

    with tmp_dir as run_dir, tmp_input_dir as input_data_dir:

        oasis_files_dir = os.path.join(run_dir, 'input')
        with tarfile.open(input_archive) as f:
            f.extractall(oasis_files_dir)

        run_args = [
            '--oasis-files-dir', oasis_files_dir,
            '--config', config_path,
            '--model-run-dir', run_dir,
            '--analysis-settings-json', analysis_settings_file,
            '--ktools-fifo-relative'
        ]

        # Optional Args:
        num_processes = settings.get('worker', 'KTOOLS_NUM_PROCESSES', fallback=None)
        if num_processes:
            run_args += ['--ktools-num-processes', num_processes]

        alloc_rule_gul = settings.get('worker', 'KTOOLS_ALLOC_RULE_GUL', fallback=None)
        if alloc_rule_gul:
            run_args += ['--ktools-alloc-rule-gul', alloc_rule_gul]

        alloc_rule_il = settings.get('worker', 'KTOOLS_ALLOC_RULE_IL', fallback=None)
        if alloc_rule_il:
            run_args += ['--ktools-alloc-rule-il', alloc_rule_il]

        alloc_rule_ri = settings.get('worker', 'KTOOLS_ALLOC_RULE_RI', fallback=None)
        if alloc_rule_ri:
            run_args += ['--ktools-alloc-rule-ri', alloc_rule_ri]

        if complex_data_files:
            prepare_complex_model_file_inputs(complex_data_files, media_root, input_data_dir)
            run_args += ['--user-data-dir', input_data_dir]

        if not settings.getboolean('worker', 'KTOOLS_ERROR_GUARD', fallback=True):
            run_args.append('--ktools-disable-guard')

        if settings.getboolean('worker', 'DEBUG_MODE', fallback=False):
            run_args.append('--verbose')
            logging.info('run_directory: {}'.format(oasis_files_dir))
            logging.info('args_list: {}'.format(str(run_args)))

        # Log MDK run command
        args_list = run_args + [''] if (len(run_args) % 2) else run_args
        mdk_args = [x for t in list(zip(*[iter(args_list)] * 2)) if (None not in t) and ('--model-run-dir' not in t) for x in t]
        logging.info("\nRUNNING: \noasislmf model generate-losses {}".format(
            " ".join([str(arg) for arg in mdk_args])
        ))

        result = subprocess.run(
            ['oasislmf', 'model', 'generate-losses'] + run_args,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # Trace back file (stdout + stderr)
        traceback_location = uuid.uuid4().hex + LOG_FILE_SUFFIX
        with open(os.path.join(settings.get('worker', 'MEDIA_ROOT'), traceback_location), 'w') as f:
            f.write(result.stdout.decode())
            f.write(result.stderr.decode())

        # Ktools log Tar file 
        log_location = uuid.uuid4().hex + ARCHIVE_FILE_SUFFIX
        log_directory = os.path.join(run_dir, "log")
        with tarfile.open(os.path.join(settings.get('worker', 'MEDIA_ROOT'), log_location), "w:gz") as tar:
            tar.add(log_directory, arcname="log")

        # Results Tar 
        output_location = uuid.uuid4().hex + ARCHIVE_FILE_SUFFIX
        output_directory = os.path.join(run_dir, "output")
        with tarfile.open(os.path.join(settings.get('worker', 'MEDIA_ROOT'), output_location), "w:gz") as tar:
            tar.add(output_directory, arcname="output")

    logging.info("Output location = {}".format(output_location))

    return output_location, traceback_location, log_location, result.returncode


@task(name='generate_input', bind=True)
def generate_input(self,
                   analysis_pk,
                   loc_file,
                   acc_file=None,
                   info_file=None,
                   scope_file=None,
                   settings_file=None,
                   complex_data_files=None):
    """Generates the input files for the loss calculation stage.

    This function is a thin wrapper around "oasislmf model generate-oasis-files".
    A temporary directory is created to contain the output oasis files.

    Args:
        analysis_pk (int): ID of the analysis. 
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
    logging.info(str(get_worker_versions()))
    notify_api_task_started(analysis_pk, self.request.id)

    media_root = settings.get('worker', 'MEDIA_ROOT')
    location_file = os.path.join(media_root, loc_file)
    accounts_file = os.path.join(media_root, acc_file) if acc_file else None
    ri_info_file = os.path.join(media_root, info_file) if info_file else None
    ri_scope_file = os.path.join(media_root, scope_file) if scope_file else None
    lookup_settings_file = os.path.join(media_root, settings_file) if settings_file else None

    model_id = settings.get('worker', 'model_id')
    config_path = get_oasislmf_config_path(model_id)

    tmp_dir = TemporaryDir(persist=settings.getboolean('worker', 'KEEP_RUN_DIR', fallback=False))
    if complex_data_files:
        tmp_input_dir = TemporaryDir(persist=settings.getboolean('worker', 'KEEP_RUN_DIR', fallback=False))
    else:
        tmp_input_dir = suppress()

    with tmp_dir as oasis_files_dir, tmp_input_dir as input_data_dir:
        run_args = [
            '--oasis-files-dir', oasis_files_dir,
            '--config', config_path,
            '--oed-location-csv', location_file,
        ]

        if accounts_file:
            run_args += ['--oed-accounts-csv', accounts_file]
        if ri_info_file:
            run_args += ['--oed-info-csv', ri_info_file]
        if ri_scope_file:
            run_args += ['--oed-scope-csv', ri_scope_file]
        if lookup_settings_file:
            run_args += ['--lookup-complex-config-json', lookup_settings_file]
        if complex_data_files:
            prepare_complex_model_file_inputs(complex_data_files, media_root, input_data_dir)
            run_args += ['--user-data-dir', input_data_dir]
        if settings.getboolean('worker', 'DISABLE_EXPOSURE_SUMMARY', fallback=False):
            run_args.append('--disable-summarise-exposure')

        # Log MDK generate command
        args_list = run_args + [''] if (len(run_args) % 2) else run_args
        mdk_args = [x for t in list(zip(*[iter(args_list)] * 2)) if None not in t for x in t]
        logging.info('run_directory: {}'.format(oasis_files_dir))
        logging.info('args_list: {}'.format(str(run_args)))
        logging.info("\nRUNNING: \noasislmf model generate-oasis-files {}".format(
            " ".join([str(arg) for arg in mdk_args])
        ))

        res = subprocess.run(['oasislmf', 'model', 'generate-oasis-files'] + run_args, stderr=subprocess.PIPE)

        # Process Generated Files
        lookup_error_fp = next(iter(glob.glob(os.path.join(oasis_files_dir, '*keys-errors*.csv'))), None)
        lookup_success_fp = next(iter(glob.glob(os.path.join(oasis_files_dir, 'gul_summary_map.csv'))), None)
        lookup_validation_fp = next(iter(glob.glob(os.path.join(oasis_files_dir, 'exposure_summary_report.json'))), None)
        summary_levels_fp = next(iter(glob.glob(os.path.join(oasis_files_dir, 'exposure_summary_levels.json'))), None)

        traceback_fp = None
        if res.stderr:
            traceback_fp = os.path.join(settings.get('worker', 'MEDIA_ROOT'), uuid.uuid4().hex + '.txt')
            with open(traceback_fp, 'w') as f:
                f.write(res.stderr.decode())

        stdout_fp = None
        if res.stdout:
            stdout_fp = os.path.join(settings.get('worker', 'MEDIA_ROOT'), uuid.uuid4().hex + '.txt')
            with open(traceback_fp, 'w') as f:
                f.write(res.stdout.decode())

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

        return {
            'output_location': output_tar_path,
            'log_location': stdout_fp,
            'error_location': traceback_fp,
            'return_code': res.returncode,
            'lookup_error_location': lookup_error_fp,
            'lookup_success_location': lookup_success_fp,
            'lookup_validation_location': lookup_validation_fp,
            'summary_levels_location': summary_levels_fp
        }


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
