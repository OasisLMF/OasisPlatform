from __future__ import absolute_import

import glob
import json
import logging
import os
import pathlib
import sys
import time

import fasteners

from contextlib import contextmanager, suppress

from celery import Celery, signature
from celery.utils.log import get_task_logger
from celery.signals import worker_ready
from celery.exceptions import WorkerLostError, Terminated


from oasislmf.utils.data import get_json
from oasislmf.utils.status import OASIS_TASK_STATUS

from ..common.filestore.filestore import get_filestore
from ..conf import celeryconf_v1 as celery_conf
from ..conf.iniconf import settings, settings_local

from .utils import (
    LoggingTaskContext,
    log_params,
    paths_to_absolute_paths,
    TemporaryDir,
    get_oasislmf_config_path,
    get_model_settings,
    get_worker_versions,
    prepare_complex_model_file_inputs,
    config_strip_default_exposure,
)

'''
Celery task wrapper for Oasis ktools calculation.
'''

LOG_FILE_SUFFIX = 'txt'
ARCHIVE_FILE_SUFFIX = 'tar.gz'
RUNNING_TASK_STATUS = OASIS_TASK_STATUS["running"]["id"]
TASK_LOG_DIR = settings.get('worker', 'TASK_LOG_DIR', fallback='/var/log/oasis/tasks')
app = Celery()
app.config_from_object(celery_conf)
model_storage = get_filestore(settings_local, "worker.model_data", raise_error=False)

logger = get_task_logger(__name__)
logger.info("Started worker")
debug_worker = settings.getboolean('worker', 'DEBUG', fallback=False)

# Quiet sub-loggers
logging.getLogger('billiard').setLevel('INFO')
logging.getLogger('numba').setLevel('INFO')


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
    logger.info(current_state)
    if current_state == RUNNING_TASK_STATUS:
        raise WorkerLostError(
            'Task received from dead worker - A worker container crashed when executing a task from analysis_id={}'.format(analysis_pk)
        )
    task.update_state(state=RUNNING_TASK_STATUS, meta={'analysis_pk': analysis_pk})

# When a worker connects send a task to the worker-monitor to register a new model


@worker_ready.connect
def register_worker(sender, **k):
    time.sleep(1)  # Workaround, pause for 1 sec to makesure log messages are printed

    m_supplier = os.environ.get('OASIS_MODEL_SUPPLIER_ID')
    m_name = os.environ.get('OASIS_MODEL_ID')
    m_id = os.environ.get('OASIS_MODEL_VERSION_ID')
    m_version = get_worker_versions()
    logger.info('Worker: SUPPLIER_ID={}, MODEL_ID={}, VERSION_ID={}'.format(m_supplier, m_name, m_id))
    logger.info('versions: {}'.format(m_version))

    # Check for 'DISABLE_WORKER_REG' before sending task to API
    if settings.getboolean('worker', 'DISABLE_WORKER_REG', fallback=False):
        logger.info(('Worker auto-registration DISABLED: to enable:\n'
                     '  set DISABLE_WORKER_REG=False in conf.ini or\n'
                     '  set the envoritment variable OASIS_DISABLE_WORKER_REG=False'))
    else:
        logger.info('Auto registrating with the Oasis API:')
        m_settings = get_model_settings(settings)
        logger.info('settings: {}'.format(m_settings))

        signature(
            'run_register_worker',
            args=(m_supplier, m_name, m_id, m_settings, m_version),
            queue='celery'
        ).delay()

    # Required ENV
    logger.info("LOCK_FILE: {}".format(settings.get('worker', 'LOCK_FILE')))
    logger.info("LOCK_TIMEOUT_IN_SECS: {}".format(settings.getfloat('worker', 'LOCK_TIMEOUT_IN_SECS')))
    logger.info("LOCK_RETRY_COUNTDOWN_IN_SECS: {}".format(settings.get('worker', 'LOCK_RETRY_COUNTDOWN_IN_SECS')))

    # Storage Mode
    selected_storage = settings.get('worker', 'STORAGE_TYPE', fallback="").lower()
    # logger.info("STORAGE_MANAGER: {}".format(type(filestore)))
    logger.info("STORAGE_TYPE: {}".format(settings.get('worker', 'STORAGE_TYPE', fallback='None')))

    if debug_worker:
        logger.info("MODEL_DATA_DIRECTORY: {}".format(settings.get('worker', 'MODEL_DATA_DIRECTORY', fallback='/home/worker/model')))
        if selected_storage in ['local-fs', 'shared-fs']:
            logger.info("MEDIA_ROOT: {}".format(settings.get('worker', 'MEDIA_ROOT')))

        elif selected_storage in ['aws-s3', 'aws', 's3']:
            logger.info("AWS_BUCKET_NAME: {}".format(settings.get('worker', 'AWS_BUCKET_NAME', fallback='None')))
            logger.info("AWS_SHARED_BUCKET: {}".format(settings.get('worker', 'AWS_SHARED_BUCKET', fallback='None')))
            logger.info("AWS_LOCATION: {}".format(settings.get('worker', 'AWS_LOCATION', fallback='None')))
            logger.info("AWS_ACCESS_KEY_ID: {}".format(settings.get('worker', 'AWS_ACCESS_KEY_ID', fallback='None')))
            logger.info("AWS_QUERYSTRING_EXPIRE: {}".format(settings.get('worker', 'AWS_QUERYSTRING_EXPIRE', fallback='None')))
            logger.info("AWS_QUERYSTRING_AUTH: {}".format(settings.get('worker', 'AWS_QUERYSTRING_AUTH', fallback='None')))
            logger.info('AWS_LOG_LEVEL: {}'.format(settings.get('worker', 'AWS_LOG_LEVEL', fallback='None')))

    # Optional ENV
    logger.info("MODEL_SETTINGS_FILE: {}".format(settings.get('worker', 'MODEL_SETTINGS_FILE', fallback='None')))
    logger.info("DISABLE_WORKER_REG: {}".format(settings.getboolean('worker', 'DISABLE_WORKER_REG', fallback='False')))
    logger.info("KEEP_RUN_DIR: {}".format(settings.get('worker', 'KEEP_RUN_DIR', fallback='False')))
    logger.info("DEBUG: {}".format(settings.get('worker', 'DEBUG', fallback='False')))
    logger.info("BASE_RUN_DIR: {}".format(settings.get('worker', 'BASE_RUN_DIR', fallback='None')))
    logger.info("OASISLMF_CONFIG: {}".format(settings.get('worker', 'oasislmf_config', fallback='None')))

    # Log Env variables
    if debug_worker:
        # show all env variables and  override root log level
        logger.info('ALL_OASIS_ENV_VARS:' + json.dumps({k: v for (k, v) in os.environ.items() if k.startswith('OASIS_')}, indent=4))
    else:
        # Limit Env variables to run only variables
        logger.info('OASIS_ENV_VARS:' + json.dumps({
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


@contextmanager
def get_lock():
    lock = fasteners.InterProcessLock(settings.get('worker', 'LOCK_FILE'))
    gotten = lock.acquire(blocking=False, timeout=settings.getfloat('worker', 'LOCK_TIMEOUT_IN_SECS'))
    yield gotten

    if gotten:
        lock.release()


# Send notification back to the API Once task is read from Queue
def notify_api_status(analysis_pk, task_status):
    logger.info("Notify API: analysis_id={}, status={}".format(
        analysis_pk,
        task_status
    ))
    signature(
        'set_task_status',
        args=(analysis_pk, task_status),
        queue='celery'
    ).delay()


def V1_task_logger(fn):

    def run(self, analysis_pk, *args):
        kwargs = {
            'log_filename': os.path.join(TASK_LOG_DIR, f"analysis_{analysis_pk}_{self.request.id}.log")
        }
        # log_level = 'DEBUG' if debug_worker else 'INFO'
        log_level = 'INFO'
        with LoggingTaskContext(logging.getLogger(), log_filename=kwargs['log_filename'], level=log_level):
            logger.info(f'====== {fn.__name__} '.ljust(90, '='))
            return fn(self, analysis_pk, *args, **kwargs)

    return run


@app.task(name='run_analysis', bind=True, acks_late=True, throws=(Terminated,))
@V1_task_logger
def start_analysis_task(self, analysis_pk, input_location, analysis_settings, complex_data_files=None, **kwargs):
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
    logger.info("LOCK_FILE: {}".format(settings.get('worker', 'LOCK_FILE')))
    logger.info("LOCK_RETRY_COUNTDOWN_IN_SECS: {}".format(
        settings.get('worker', 'LOCK_RETRY_COUNTDOWN_IN_SECS')))

    with get_lock() as gotten:
        if not gotten:
            logger.info("Failed to get resource lock - retry task")
            raise self.retry(
                max_retries=None,
                countdown=settings.getint('worker', 'LOCK_RETRY_COUNTDOWN_IN_SECS'))

        logger.info("Acquired resource lock")

        try:
            # Check if this task was re-queued from a lost worker
            check_worker_lost(self, analysis_pk)

            notify_api_status(analysis_pk, 'RUN_STARTED')
            self.update_state(state=RUNNING_TASK_STATUS)
            output_location, traceback_location, log_location, return_code = start_analysis(
                analysis_settings,
                input_location,
                complex_data_files=complex_data_files,
                **kwargs
            )

        except Terminated:
            sys.exit('Task aborted')
        except Exception:
            logger.exception("Model execution task failed.")
            raise

        return output_location, traceback_location, log_location, return_code


def start_analysis(analysis_settings, input_location, complex_data_files=None, **kwargs):
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
    filestore = get_filestore(settings)
    from oasislmf.manager import OasisManager

    logger.info("args: {}".format(str(locals())))
    logger.info(str(get_worker_versions()))
    tmpdir_persist = settings.getboolean('worker', 'KEEP_RUN_DIR', fallback=False)
    tmpdir_base = settings.get('worker', 'BASE_RUN_DIR', fallback=None)

    tmp_dir = TemporaryDir(persist=tmpdir_persist, basedir=tmpdir_base)

    if complex_data_files:
        tmp_input_dir = TemporaryDir(persist=tmpdir_persist, basedir=tmpdir_base)
    else:
        tmp_input_dir = suppress()

    with tmp_dir as run_dir, tmp_input_dir as input_data_dir:

        # Fetch generated inputs
        oasis_files_dir = os.path.join(run_dir, 'input')
        analysis_settings_file = filestore.get(analysis_settings, os.path.join(run_dir, 'analysis_settings.json'), required=True)
        filestore.extract(input_location, oasis_files_dir)

        # oasislmf.json
        config_path = get_oasislmf_config_path(settings)
        config = config_strip_default_exposure(get_json(config_path))
        task_params = {
            'oasis_files_dir': oasis_files_dir,
            'model_run_dir': run_dir,
            'analysis_settings_json': analysis_settings_file,
            'ktools_fifo_relative': True,
            'verbose': debug_worker,
            # 'df_engine': json.dumps({
            #     "path": settings.get(
            #         'worker',
            #         'default_reader_engine',
            #         fallback='oasis_data_manager.df_reader.reader.OasisPandasReader'
            #     ),
            #     "options": settings.get(
            #         'worker.default_reader_engine_options',
            #         None,
            #         fallback={}
            #     ),
            # }),
        }

        # Set model storage
        if model_storage:
            model_storage_settings_file = os.path.join(run_dir, 'model_storage.json')
            with open(model_storage_settings_file, "w") as f:
                config = model_storage.to_config()
                # config["options"]["root_dir"] = os.path.join(
                #    config["options"].get("root_dir", ""),
                #    settings.get("worker", "MODEL_SUPPLIER_ID"),
                #    settings.get("worker", "MODEL_ID"),
                #    settings.get("worker", "MODEL_VERSION_ID"),
                # )
                json.dump(model_storage.to_config(), f, indent=4)
            task_params['model_storage_json'] = model_storage_settings_file

        if complex_data_files:
            prepare_complex_model_file_inputs(complex_data_files, input_data_dir, filestore)
            task_params['user_data_dir'] = input_data_dir

        # Create and log params
        run_params = {**config, **task_params}
        gen_losses_params = OasisManager()._params_generate_oasis_losses(**run_params)
        params = paths_to_absolute_paths({**gen_losses_params}, config_path)

        if debug_worker:
            log_params(params, kwargs)

        # Store run settings
        run_params_file = os.path.join(run_dir, 'oasislmf.json')
        with open(run_params_file, "w") as f:
            json.dump(params, f, indent=4)

        # Run generate losses
        try:
            OasisManager().generate_oasis_losses(**params)
            returncode = 0
        except Exception as e:
            logger.exception("Error occured in 'generate_oasis_losses':")
            returncode = 1

        # Ktools log Tar file
        traceback_location = filestore.put(kwargs['log_filename'])
        log_directory = os.path.join(run_dir, "log")
        log_location = filestore.put(log_directory, suffix=ARCHIVE_FILE_SUFFIX)

        # Results dir & analysis-settings
        output_directory = os.path.join(run_dir, "output")
        output_location = filestore.put(output_directory, suffix=ARCHIVE_FILE_SUFFIX, arcname='output')

    return output_location, traceback_location, log_location, returncode


@app.task(name='generate_input', bind=True, acks_late=True, throws=(Terminated,))
@V1_task_logger
def generate_input(self,
                   analysis_pk,
                   loc_file,
                   acc_file=None,
                   info_file=None,
                   scope_file=None,
                   settings_file=None,
                   complex_data_files=None,
                   **kwargs):
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
    logging.info(str(get_worker_versions()))

    # Check if this task was re-queued from a lost worker
    check_worker_lost(self, analysis_pk)

    # Start Oasis file generation
    notify_api_status(analysis_pk, 'INPUTS_GENERATION_STARTED')
    filestore = get_filestore(settings)
    from oasislmf.manager import OasisManager

    # filestore.media_root = settings.get('worker', 'MEDIA_ROOT')
    tmpdir_persist = settings.getboolean('worker', 'KEEP_RUN_DIR', fallback=False)
    tmpdir_base = settings.get('worker', 'BASE_RUN_DIR', fallback=None)

    tmp_dir = TemporaryDir(persist=tmpdir_persist, basedir=tmpdir_base)
    if complex_data_files:
        tmp_input_dir = TemporaryDir(persist=tmpdir_persist, basedir=tmpdir_base)
    else:
        tmp_input_dir = suppress()

    with tmp_dir as oasis_files_dir, tmp_input_dir as input_data_dir:
        task_params = {'oasis_files_dir': oasis_files_dir}
        model_settings_fp = settings.get('worker', 'MODEL_SETTINGS_FILE', fallback='')
        task_params['model_settings_file'] = model_settings_fp if model_settings_fp and os.path.isfile(model_settings_fp) else None

        # Fetch input files
        if loc_file:
            loc_extention = "".join(pathlib.Path(loc_file).suffixes)
            task_params['oed_location_csv'] = filestore.get(
                loc_file,
                os.path.join(oasis_files_dir, f'location{loc_extention}')
            )
        if acc_file:
            acc_extention = "".join(pathlib.Path(acc_file).suffixes)
            task_params['oed_accounts_csv'] = filestore.get(
                acc_file,
                os.path.join(oasis_files_dir, f'account{acc_extention}')
            )
        if info_file:
            info_extention = "".join(pathlib.Path(info_file).suffixes)
            task_params['oed_info_csv'] = filestore.get(
                info_file,
                os.path.join(oasis_files_dir, f'reinsinfo{info_extention}')
            )
        if scope_file:
            scope_extention = "".join(pathlib.Path(scope_file).suffixes)
            task_params['oed_scope_csv'] = filestore.get(
                scope_file,
                os.path.join(oasis_files_dir, f'reinsscope{scope_extention}')
            )
        if settings_file:
            task_params['analysis_settings_json'] = task_params['lookup_complex_config_json'] = filestore.get(
                settings_file,
                os.path.join(oasis_files_dir, 'analysis_settings.json')
            )
        if complex_data_files:
            prepare_complex_model_file_inputs(complex_data_files, input_data_dir, filestore)
            task_params['user_data_dir'] = input_data_dir

        config_path = get_oasislmf_config_path(settings)
        config = config_strip_default_exposure(get_json(config_path))
        lookup_params = {**config, **task_params}
        gen_files_params = OasisManager()._params_generate_oasis_files(**lookup_params)
        params = paths_to_absolute_paths({**gen_files_params}, config_path)

        if debug_worker:
            log_params(params, kwargs, exclude_keys=[
                'profile_loc',
                'profile_loc_json',
                'profile_acc',
                'profile_fm_agg',
                'profile_fm_agg_json',
                'fm_aggregation_profile',
                'accounts_profile',
                'oed_hierarchy',
                'exposure_profile',
                'lookup_config',
            ])

        # Store run settings
        if debug_worker:
            run_params_file = os.path.join(oasis_files_dir, 'oasislmf.json')
            with open(run_params_file, "w") as f:
                json.dump(params, f, indent=4)

        try:
            OasisManager().generate_oasis_files(**params)
            returncode = 0
        except Exception as e:
            logger.exception("Error occured in 'generate_oasis_files':")
            returncode = 1

        # Find Generated Files
        lookup_error_fp = next(iter(glob.glob(os.path.join(oasis_files_dir, '*keys-errors*.csv'))), None)
        lookup_success_fp = next(iter(glob.glob(os.path.join(oasis_files_dir, 'gul_summary_map.csv'))), None)
        lookup_validation_fp = next(iter(glob.glob(os.path.join(oasis_files_dir, 'exposure_summary_report.json'))), None)
        summary_levels_fp = next(iter(glob.glob(os.path.join(oasis_files_dir, 'exposure_summary_levels.json'))), None)

        # Store logs
        traceback = filestore.put(kwargs['log_filename'])
        filestore.get(traceback, os.path.join(oasis_files_dir, os.path.basename(kwargs['log_filename'])))

        # Store result files
        lookup_error = filestore.put(lookup_error_fp)
        lookup_success = filestore.put(lookup_success_fp)
        lookup_validation = filestore.put(lookup_validation_fp)
        summary_levels = filestore.put(summary_levels_fp)
        output_tar_path = filestore.put(oasis_files_dir)
        return output_tar_path, lookup_error, lookup_success, lookup_validation, summary_levels, traceback, returncode


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
        ).delay()
