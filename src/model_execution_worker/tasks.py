from __future__ import absolute_import

import glob
import json
import logging
import os
import subprocess
import shutil

import fasteners
import tempfile
import tarfile

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
from .storage_manager import StorageSelector

'''
Celery task wrapper for Oasis ktools calculation.
'''

LOG_FILE_SUFFIX = 'txt'
ARCHIVE_FILE_SUFFIX = 'tar.gz'
RUNNING_TASK_STATUS = OASIS_TASK_STATUS["running"]["id"]
CELERY = Celery()
CELERY.config_from_object(celery_conf)
logging.info("Started worker")

filestore = StorageSelector(settings)


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


def get_oasislmf_config_path(model_id=None):
    conf_var = settings.get('worker', 'oasislmf_config', fallback=None)
    if not model_id:
        model_id = settings.get('worker', 'model_id')

    if conf_var:
        return conf_var

    model_root = settings.get('worker', 'model_data_directory', fallback='/var/oasis/')
    model_specific_conf = Path(model_root, '{}-oasislmf.json'.format(model_id))
    if model_specific_conf.exists():
        return str(model_specific_conf)

    return str(Path(model_root, 'oasislmf.json'))


# Send notification back to the API Once task is read from Queue
def notify_api_status(analysis_pk, task_status):
    logging.info("Notify API: analysis_id={}, status={}".format(
        analysis_pk,
        task_status
    ))
    signature(
        'set_task_status',
        args=(analysis_pk, task_status),
        queue='celery'
    ).delay()


@task(name='run_analysis', bind=True)
def start_analysis_task(self, analysis_pk, input_location, analysis_settings, complex_data_files=None):
    """Task wrapper for running an analysis.

    Args:
        self: Celery task instance.
        analysis_settings (str): Path or URL to the analysis settings.
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
            notify_api_status(analysis_pk, 'RUN_STARTED')
            self.update_state(state=RUNNING_TASK_STATUS)
            output_location, traceback_location, log_location, return_code = start_analysis(
                analysis_settings,
                input_location,
                complex_data_files=complex_data_files
            )
        except Exception:
            logging.exception("Model execution task failed.")
            raise

        return output_location, traceback_location, log_location, return_code


@oasis_log()
def start_analysis(analysis_settings, input_location, complex_data_files=None):
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

    config_path = get_oasislmf_config_path()
    tmp_dir = TemporaryDir(persist=settings.getboolean('worker', 'KEEP_RUN_DIR', fallback=False))

    if complex_data_files:
        tmp_input_dir = TemporaryDir(persist=settings.getboolean('worker', 'KEEP_RUN_DIR', fallback=False))
    else:
        tmp_input_dir = suppress()

    with tmp_dir as run_dir, tmp_input_dir as input_data_dir:

        # Fetch generated inputs
        analysis_settings_file = filestore.get(analysis_settings, run_dir)
        input_archive = filestore.get(input_location, run_dir)
        if not os.path.exists(input_archive):
            raise MissingInputsException(input_archive)
        if not tarfile.is_tarfile(input_archive):
            raise InvalidInputsException(input_archive)

        oasis_files_dir = os.path.join(run_dir, 'input')
        filestore.extract(input_archive, oasis_files_dir)

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
            prepare_complex_model_file_inputs(complex_data_files, input_data_dir)
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
        logging.info(run_args)
        result = subprocess.run(
            ['oasislmf', 'model', 'generate-losses'] + run_args,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        logging.info('stdout: {}'.format(result.stdout.decode()))
        logging.info('stderr: {}'.format(result.stderr.decode()))

        # Traceback file (stdout + stderr)
        traceback_file = filestore.create_traceback(result, run_dir)
        traceback_location = filestore.put(traceback_file)

        # Ktools log Tar file
        log_directory = os.path.join(run_dir, "log")
        log_location = filestore.put(log_directory, suffix=ARCHIVE_FILE_SUFFIX)

        # Results dir
        output_directory = os.path.join(run_dir, "output")
        output_location = filestore.put(output_directory, suffix=ARCHIVE_FILE_SUFFIX, arcname='output')

    return output_location, traceback_location, log_location, result.returncode


@task(name='generate_input')
def generate_input(analysis_pk,
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
    notify_api_status(analysis_pk, 'INPUTS_GENERATION_STARTED')

    media_root = settings.get('worker', 'MEDIA_ROOT')

    config_path = get_oasislmf_config_path()

    tmp_dir = TemporaryDir(persist=settings.getboolean('worker', 'KEEP_RUN_DIR', fallback=False))
    if complex_data_files:
        tmp_input_dir = TemporaryDir(persist=settings.getboolean('worker', 'KEEP_RUN_DIR', fallback=False))
    else:
        tmp_input_dir = suppress()

    with tmp_dir as oasis_files_dir, tmp_input_dir as input_data_dir:

        # Fetch input files
        location_file        = filestore.get(loc_file, oasis_files_dir)
        accounts_file        = filestore.get(acc_file, oasis_files_dir)
        ri_info_file         = filestore.get(info_file, oasis_files_dir)
        ri_scope_file        = filestore.get(scope_file, oasis_files_dir)
        lookup_settings_file = filestore.get(settings_file, oasis_files_dir)

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
            prepare_complex_model_file_inputs(complex_data_files, input_data_dir)
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

        result = subprocess.run(['oasislmf', 'model', 'generate-oasis-files'] + run_args,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        logging.info('stdout: {}'.format(result.stdout.decode()))
        logging.info('stderr: {}'.format(result.stderr.decode()))

        # Find Generated Files
        lookup_error_fp = next(iter(glob.glob(os.path.join(oasis_files_dir, '*keys-errors*.csv'))), None)
        lookup_success_fp = next(iter(glob.glob(os.path.join(oasis_files_dir, 'gul_summary_map.csv'))), None)
        lookup_validation_fp = next(iter(glob.glob(os.path.join(oasis_files_dir, 'exposure_summary_report.json'))), None)
        summary_levels_fp = next(iter(glob.glob(os.path.join(oasis_files_dir, 'exposure_summary_levels.json'))), None)

        # Store result files
        traceback_file    = filestore.create_traceback(result, oasis_files_dir)
        traceback         = filestore.put(traceback_file)
        lookup_error      = filestore.put(lookup_error_fp)
        lookup_success    = filestore.put(lookup_success_fp)
        lookup_validation = filestore.put(lookup_validation_fp)
        summary_levels    = filestore.put(summary_levels_fp)
        output_tar_path   = filestore.put(oasis_files_dir)

        return output_tar_path, lookup_error, lookup_success, lookup_validation, summary_levels, traceback, result.returncode


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


def prepare_complex_model_file_inputs(complex_model_files, run_directory):
    """Places the specified complex model files in the run_directory.

    The unique upload filenames are converted back to the original upload names, so that the
    names match any input configuration file.

    On Linux, the files are symlinked, whereas on Windows the files are simply copied.

    Args:
        complex_model_files (list of complex_model_data_file): List of dicts giving the files
            to make available.
        run_directory (str): Model inputs directory to place the files in.

    Returns:
        None.

    """
    for cmf in complex_model_files:
        stored_fn = cmf[STORED_FILENAME]
        orig_fn = cmf[ORIGINAL_FILENAME]

        if filestore._is_valid_url(stored_fn):
            # If reference is a URL, then download the file & rename to 'original_filename'
            fpath = filestore.get(stored_fn, run_directory)
            shutil.move(fpath, os.path.join(run_directory, orig_fn))
        elif os.path.isfile(stored_fn):
            # If refrence is local filepath check that it exisits and copy/symlink
            from_path = filestore.get(stored_fn)
            to_path = os.path.join(run_directory, orig_fn)
            if os.name == 'nt':
                shutil.copy(from_path, to_path)
            else:
                os.symlink(from_path, to_path)
        else:
            logging.info('WARNING: failed to get complex model file "{}"'.format(stored_fn))
            #raise OSError("Complex model file not found: {}".format(stored_fn))
