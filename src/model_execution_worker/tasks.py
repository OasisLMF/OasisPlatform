from __future__ import absolute_import

import glob
import json
import logging
import os
import sys
import shutil
import subprocess

import fasteners
import tempfile
import tarfile

from contextlib import contextmanager, suppress
from packaging import version

from celery import Celery, signature
from celery.signals import worker_ready
from celery.exceptions import WorkerLostError, Terminated
from celery.platforms import signals

from oasislmf.utils.data import get_json
from oasislmf.utils.exceptions import OasisException
from oasislmf.utils.log import oasis_log
from oasislmf.utils.status import OASIS_TASK_STATUS
from oasislmf import __version__ as mdk_version
from pathlib2 import Path

from ..conf import celeryconf as celery_conf
from ..conf.iniconf import settings
from ..common.data import STORED_FILENAME, ORIGINAL_FILENAME

# from .storage_manager import StorageSelector
from .storage_manager import BaseStorageConnector
from .backends.aws_storage import AwsObjectStore
from .backends.azure_storage import AzureObjectStore

'''
Celery task wrapper for Oasis ktools calculation.
'''

LOG_FILE_SUFFIX = 'txt'
ARCHIVE_FILE_SUFFIX = 'tar.gz'
RUNNING_TASK_STATUS = OASIS_TASK_STATUS["running"]["id"]
app = Celery()
app.config_from_object(celery_conf)
logging.info("Started worker")
debug_worker = settings.getboolean('worker', 'DEBUG', fallback=False)

# Set storage manager
selected_storage = settings.get('worker', 'STORAGE_TYPE', fallback="").lower()
if selected_storage in ['local-fs', 'shared-fs']:
    filestore = BaseStorageConnector(settings)
elif selected_storage in ['aws-s3', 'aws', 's3']:
    filestore = AwsObjectStore(settings)
elif selected_storage in ['azure']:
    filestore = AzureObjectStore(settings)
else:
    raise OasisException('Invalid value for STORAGE_TYPE: {}'.format(selected_storage))


class TemporaryDir(object):
    """Context manager for mkdtemp() with option to persist"""

    def __init__(self, persist=False, basedir=None):
        self.persist = persist
        self.basedir = basedir

        if basedir:
            os.makedirs(basedir, exist_ok=True)

    def __enter__(self):
        self.name = tempfile.mkdtemp(dir=self.basedir)
        return self.name

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.persist and os.path.isdir(self.name):
            shutil.rmtree(self.name)


def get_oasislmf_config_path(model_id=None):
    """ Search for the oasislmf confiuration file
    """
    conf_path = None
    model_root = settings.get('worker', 'model_data_directory', fallback='/home/worker/model')

    # 1: Explicit location
    conf_path = Path(settings.get('worker', 'oasislmf_config', fallback=""))
    if conf_path.is_file():
        return str(conf_path)

    # 2: try 'model specific conf'
    if model_id:
        conf_path = Path(model_root, '{}-oasislmf.json'.format(model_id))
        if conf_path.is_file():
            return str(conf_path)

    # 3: Try generic model conf
    conf_path = Path(model_root, 'oasislmf.json')
    if conf_path.is_file():
        return str(conf_path)

    # 4: check compatibility look for older model mount
    conf_path = Path('/var/oasis', 'oasislmf.json')
    if conf_path.is_file():
        return str(conf_path)

    # 5: warn and return fallback
    logging.warning("WARNING: 'oasislmf.json' Configuration file not found")
    return str(Path(model_root, 'oasislmf.json'))


def get_model_settings():
    """ Read the settings file from the path OASIS_MODEL_SETTINGS
        returning the contents as a python dicself.t (none if not found)
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


def check_worker_lost(task, analysis_pk):
    """
    SAFE GUARD: - Fail any tasks received from dead workers
    -------------------------------------------------------
    Setting the option `acks_late` means tasks will remain on the Queue until after
    a tasks has completed. If the worker goes down during the execution of `generate_input`
    or `start_analysis_task` then if another work is available the task will be picked up
    on an active worker.

    When the task is picked up for a 2nd time, the new worker will reject it will
    'WorkerLostError' and mark the execution as failed.

    Note that this is not the ideal approach, since at least one alive worker is required to
    fail as crash workers task.

    A better method is to use either tasks signals or celery events to fail the task immediately,
    so this should be viewed as a fallback option.
    """
    current_state = task.AsyncResult(task.request.id).state
    logging.info(current_state)
    if current_state == RUNNING_TASK_STATUS:
        raise WorkerLostError(
            'Task received from dead worker - A worker container crashed when executing a task from analysis_id={}'.format(analysis_pk)
        )
    task.update_state(state=RUNNING_TASK_STATUS, meta={'analysis_pk': analysis_pk})


# When a worker connects send a task to the worker-monitor to register a new model
@worker_ready.connect
def register_worker(sender, **k):
    m_supplier = os.environ.get('OASIS_MODEL_SUPPLIER_ID')
    m_name = os.environ.get('OASIS_MODEL_ID')
    m_id = os.environ.get('OASIS_MODEL_VERSION_ID')
    m_version = get_worker_versions()
    m_conf = get_json(get_oasislmf_config_path(m_id))

    logging.info('Worker: SUPPLIER_ID={}, MODEL_ID={}, VERSION_ID={}'.format(m_supplier, m_name, m_id))
    logging.info('versions: {}'.format(m_version))
    logging.info('oasislmf config: {}'.format(m_conf))

    # Check for 'DISABLE_WORKER_REG' before sending task to API
    if settings.getboolean('worker', 'DISABLE_WORKER_REG', fallback=False):
        logging.info(('Worker auto-registration DISABLED: to enable:\n'
                      '  set DISABLE_WORKER_REG=False in conf.ini or\n'
                      '  set the envoritment variable OASIS_DISABLE_WORKER_REG=False'))
    else:
        logging.info('Auto registrating with the Oasis API:')
        m_settings = get_model_settings()
        logging.info('settings: {}'.format(m_settings))

        signature(
            'run_register_worker',
            args=(m_supplier, m_name, m_id, m_settings, m_version, m_conf),
        ).delay()

    # Required ENV
    logging.info("LOCK_FILE: {}".format(settings.get('worker', 'LOCK_FILE')))
    logging.info("LOCK_TIMEOUT_IN_SECS: {}".format(settings.getfloat('worker', 'LOCK_TIMEOUT_IN_SECS')))
    logging.info("LOCK_RETRY_COUNTDOWN_IN_SECS: {}".format(settings.get('worker', 'LOCK_RETRY_COUNTDOWN_IN_SECS')))

    # Storage Mode
    selected_storage = settings.get('worker', 'STORAGE_TYPE', fallback="").lower()
    logging.info("STORAGE_MANAGER: {}".format(type(filestore)))
    logging.info("STORAGE_TYPE: {}".format(settings.get('worker', 'STORAGE_TYPE', fallback='None')))

    if debug_worker:
        logging.info("MODEL_DATA_DIRECTORY: {}".format(settings.get('worker', 'MODEL_DATA_DIRECTORY', fallback='/home/worker/model')))
        if selected_storage in ['local-fs', 'shared-fs']:
            logging.info("MEDIA_ROOT: {}".format(settings.get('worker', 'MEDIA_ROOT')))

        elif selected_storage in ['aws-s3', 'aws', 's3']:
            logging.info("AWS_BUCKET_NAME: {}".format(settings.get('worker', 'AWS_BUCKET_NAME', fallback='None')))
            logging.info("AWS_SHARED_BUCKET: {}".format(settings.get('worker', 'AWS_SHARED_BUCKET', fallback='None')))
            logging.info("AWS_LOCATION: {}".format(settings.get('worker', 'AWS_LOCATION', fallback='None')))
            logging.info("AWS_ACCESS_KEY_ID: {}".format(settings.get('worker', 'AWS_ACCESS_KEY_ID', fallback='None')))
            logging.info("AWS_QUERYSTRING_EXPIRE: {}".format(settings.get('worker', 'AWS_QUERYSTRING_EXPIRE', fallback='None')))
            logging.info("AWS_QUERYSTRING_AUTH: {}".format(settings.get('worker', 'AWS_QUERYSTRING_AUTH', fallback='None')))
            logging.info('AWS_LOG_LEVEL: {}'.format(settings.get('worker', 'AWS_LOG_LEVEL', fallback='None')))

    # Optional ENV
    logging.info("MODEL_SETTINGS_FILE: {}".format(settings.get('worker', 'MODEL_SETTINGS_FILE', fallback='None')))
    logging.info("DISABLE_WORKER_REG: {}".format(settings.getboolean('worker', 'DISABLE_WORKER_REG', fallback='False')))
    logging.info("KEEP_RUN_DIR: {}".format(settings.get('worker', 'KEEP_RUN_DIR', fallback='False')))
    logging.info("DEBUG: {}".format(settings.get('worker', 'DEBUG', fallback='False')))
    logging.info("BASE_RUN_DIR: {}".format(settings.get('worker', 'BASE_RUN_DIR', fallback='None')))
    logging.info("OASISLMF_CONFIG: {}".format(settings.get('worker', 'oasislmf_config', fallback='None')))

    # Log Env variables
    if debug_worker:
        # show all env variables and  override root log level
        logging.info('ALL_OASIS_ENV_VARS:' + json.dumps({k: v for (k, v) in os.environ.items() if k.startswith('OASIS_')}, indent=4))
    else:
        # Limit Env variables to run only variables
        logging.info('OASIS_ENV_VARS:' + json.dumps({
            k: v for (k, v) in os.environ.items() if k.startswith('OASIS_') and not any(
                substring in k for substring in [
                    'SERVER',
                    'CELERY',
                    'RABBIT',
                    'BROKER',
                    'USER',
                    'PASS',
                    'PORT',
                    'HOST',
                    'ROOT',
                    'DIR',
                ])}, indent=4))

    # Clean up multiprocess tmp dirs on startup
    for tmpdir in glob.glob("/tmp/pymp-*"):
        os.rmdir(tmpdir)


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


@app.task(name='run_analysis', bind=True, acks_late=True, throws=(Terminated,))
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
            # Check if this task was re-queued from a lost worker
            check_worker_lost(self, analysis_pk)

            notify_api_status(analysis_pk, 'RUN_STARTED')
            self.update_state(state=RUNNING_TASK_STATUS)
            output_location, traceback_location, log_location, return_code = start_analysis(
                analysis_settings,
                input_location,
                complex_data_files=complex_data_files
            )

        except Terminated:
            sys.exit('Task aborted')
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
    tmpdir_persist = settings.getboolean('worker', 'KEEP_RUN_DIR', fallback=False)
    tmpdir_base = settings.get('worker', 'BASE_RUN_DIR', fallback=None)

    # Setup Job cancellation handler

    def analysis_cancel_handler(signum, frame):
        logging.info('TASK CANCELLATION')
        if proc is not None:
            os.killpg(os.getpgid(proc.pid), 15)
        raise Terminated("Cancellation request sent from API")

    proc = None  # Popen object for subpross runner
    signals['SIGTERM'] = analysis_cancel_handler

    config_path = get_oasislmf_config_path()
    tmp_dir = TemporaryDir(persist=tmpdir_persist, basedir=tmpdir_base)
    filestore.media_root = settings.get('worker', 'MEDIA_ROOT')

    if complex_data_files:
        tmp_input_dir = TemporaryDir(persist=tmpdir_persist, basedir=tmpdir_base)
    else:
        tmp_input_dir = suppress()

    with tmp_dir as run_dir, tmp_input_dir as input_data_dir:

        # Fetch generated inputs
        analysis_settings_file = filestore.get(analysis_settings, run_dir, required=True)
        input_archive = filestore.get(input_location, run_dir, required=True)
        if not tarfile.is_tarfile(input_archive):
            raise InvalidInputsException(input_archive)

        oasis_files_dir = os.path.join(run_dir, 'input')
        filestore.extract(input_archive, oasis_files_dir)

        run_args = [
            '--oasis-files-dir', oasis_files_dir,
            '--config', config_path,
            '--model-run-dir', run_dir,
            '--analysis-settings-json', analysis_settings_file,
            '--ktools-fifo-relative',
            '--verbose'
        ]

        if complex_data_files:
            prepare_complex_model_file_inputs(complex_data_files, input_data_dir)
            run_args += ['--user-data-dir', input_data_dir]

        # check version and load model_settings for default samples if given
        if version.parse(mdk_version) > version.parse("1.26.0"):
            model_settings_fp = settings.get('worker', 'MODEL_SETTINGS_FILE', fallback='')
            if model_settings_fp and os.path.isfile(model_settings_fp):
                run_args += ['--model-settings-json', model_settings_fp]

        # Log MDK run command
        args_list = run_args + [''] if (len(run_args) % 2) else run_args
        mdk_args = [x for t in list(zip(*[iter(args_list)] * 2)) if (None not in t) and ('--model-run-dir' not in t) for x in t]
        logging.info('run_directory: {}'.format(oasis_files_dir))
        # logging.info('args_list: {}'.format(str(run_args)))
        logging.info("\nExecuting: generate-losses")
        if debug_worker:
            logging.info("\nCLI command: \noasislmf model generate-losses {}".format(
                " ".join([str(arg) for arg in mdk_args])
            ))
            logging.info(run_args)

        # Subprocess Execution
        worker_env = os.environ.copy()

        proc = subprocess.Popen(
            ['oasislmf', 'model', 'generate-losses'] + run_args,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=worker_env,
            preexec_fn=os.setsid,   # run the program in a new session, assigning a new process group to it and its children.
        )
        stdout, stderr = proc.communicate()

        if debug_worker:
            logging.info('stdout: {}'.format(stdout.decode()))

        logging.info('stderr: {}'.format(stderr.decode()))
        proc.terminate()

        # Traceback file (stdout + stderr)
        traceback_file = filestore.create_traceback(stdout.decode(), stderr.decode(), run_dir)
        traceback_location = filestore.put(traceback_file)

        # Ktools log Tar file
        log_directory = os.path.join(run_dir, "log")
        log_location = filestore.put(log_directory, suffix=ARCHIVE_FILE_SUFFIX)

        # Results dir & analysis-settings
        output_directory = os.path.join(run_dir, "output")
        output_location = filestore.put(output_directory, suffix=ARCHIVE_FILE_SUFFIX, arcname='output')

    return output_location, traceback_location, log_location, proc.returncode


@app.task(name='generate_input', bind=True, acks_late=True, throws=(Terminated,))
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

    # Check if this task was re-queued from a lost worker
    check_worker_lost(self, analysis_pk)

    # Setup Job cancellation handler
    def generate_input_cancel_handler(signum, frame):
        logging.info('TASK CANCELLATION')
        if proc is not None:
            os.killpg(os.getpgid(proc.pid), 15)
        raise Terminated("Cancellation request sent from API")

    proc = None  # Popen object for subpross runner
    signals['SIGTERM'] = generate_input_cancel_handler

    # Start Oasis file generation
    notify_api_status(analysis_pk, 'INPUTS_GENERATION_STARTED')
    filestore.media_root = settings.get('worker', 'MEDIA_ROOT')
    config_path = get_oasislmf_config_path()
    tmpdir_persist = settings.getboolean('worker', 'KEEP_RUN_DIR', fallback=False)
    tmpdir_base = settings.get('worker', 'BASE_RUN_DIR', fallback=None)

    tmp_dir = TemporaryDir(persist=tmpdir_persist, basedir=tmpdir_base)
    if complex_data_files:
        tmp_input_dir = TemporaryDir(persist=tmpdir_persist, basedir=tmpdir_base)
    else:
        tmp_input_dir = suppress()

    with tmp_dir as oasis_files_dir, tmp_input_dir as input_data_dir:

        # Fetch input files
        location_file = filestore.get(loc_file, oasis_files_dir, required=True)
        accounts_file = filestore.get(acc_file, oasis_files_dir)
        ri_info_file = filestore.get(info_file, oasis_files_dir)
        ri_scope_file = filestore.get(scope_file, oasis_files_dir)
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

        model_settings_fp = settings.get('worker', 'MODEL_SETTINGS_FILE', fallback='')
        if model_settings_fp and os.path.isfile(model_settings_fp):
            run_args += ['--model-settings-json', model_settings_fp]

        if debug_worker:
            run_args += ['--verbose']

        # Log MDK generate command
        args_list = run_args + [''] if (len(run_args) % 2) else run_args
        mdk_args = [x for t in list(zip(*[iter(args_list)] * 2)) if None not in t for x in t]
        logging.info('run_directory: {}'.format(oasis_files_dir))
        # logging.info('args_list: {}'.format(str(run_args)))
        logging.info("\nExecuting: generate-oasis-files")
        if debug_worker:
            logging.info("\nCLI command: \noasislmf model generate-oasis-files {}".format(
                " ".join([str(arg) for arg in mdk_args])
            ))

        # Subprocess Execution
        worker_env = os.environ.copy()
        proc = subprocess.Popen(
            ['oasislmf', 'model', 'generate-oasis-files'] + run_args,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=worker_env,
            preexec_fn=os.setsid,  # run in a new session, assigning a new process group to it and its children.
        )
        stdout, stderr = proc.communicate()

        # Log output and close
        if debug_worker:
            logging.info('stdout: {}'.format(stdout.decode()))
        logging.info('stderr: {}'.format(stderr.decode()))
        proc.terminate()

        # Find Generated Files
        lookup_error_fp = next(iter(glob.glob(os.path.join(oasis_files_dir, '*keys-errors*.csv'))), None)
        lookup_success_fp = next(iter(glob.glob(os.path.join(oasis_files_dir, 'gul_summary_map.csv'))), None)
        lookup_validation_fp = next(iter(glob.glob(os.path.join(oasis_files_dir, 'exposure_summary_report.json'))), None)
        summary_levels_fp = next(iter(glob.glob(os.path.join(oasis_files_dir, 'exposure_summary_levels.json'))), None)

        # Store result files
        traceback_file = filestore.create_traceback(stdout.decode(), stderr.decode(), oasis_files_dir)
        traceback = filestore.put(traceback_file)
        lookup_error = filestore.put(lookup_error_fp)
        lookup_success = filestore.put(lookup_success_fp)
        lookup_validation = filestore.put(lookup_validation_fp)
        summary_levels = filestore.put(summary_levels_fp)
        output_tar_path = filestore.put(oasis_files_dir)
        return output_tar_path, lookup_error, lookup_success, lookup_validation, summary_levels, traceback, proc.returncode


@app.task(name='on_error')
def on_error(request, ex, traceback, record_task_name, analysis_pk, initiator_pk):
    """
    Because of how celery works we need to include a celery task registered in the
    current app to pass to the `link_error` function on a chain.

    This function takes the error and passes it on back to the server so that it can store
    the info on the analysis.
    """
    # Ignore exceptions raised from Job cancellations
    if not isinstance(ex, Terminated):
        signature(
            record_task_name,
            args=(analysis_pk, initiator_pk, traceback),
            queue='celery'
        ).delay({})


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
        elif filestore._is_stored(stored_fn):
            # If refrence is local filepath check that it exisits and copy/symlink
            from_path = filestore.get(stored_fn)
            to_path = os.path.join(run_directory, orig_fn)
            if os.name == 'nt':
                logging.info(f'complex_model_file: copy {from_path} to {to_path}')
                shutil.copy(from_path, to_path)
            else:
                logging.info(f'complex_model_file: link {from_path} to {to_path}')
                os.symlink(from_path, to_path)
        else:
            logging.info('WARNING: failed to get complex model file "{}"'.format(stored_fn))
