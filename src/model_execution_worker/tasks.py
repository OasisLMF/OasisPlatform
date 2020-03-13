from __future__ import absolute_import

import glob
import json
import logging
import os
import subprocess
from datetime import datetime
import shutil
import uuid

import fasteners
import tempfile
import tarfile

from contextlib import contextmanager, suppress

from celery import Celery, signature
from celery.task import task
from celery.signals import worker_ready, before_task_publish
from oasislmf.manager import OasisManager
from oasislmf.model_preparation.lookup import OasisLookupFactory
from oasislmf.utils.data import get_json, get_dataframe
from oasislmf.utils.exceptions import OasisException
from oasislmf.utils.log import oasis_log
from oasislmf.utils.status import OASIS_TASK_STATUS
from oasislmf import __version__ as mdk_version
from pathlib2 import Path
import pandas as pd

from ..conf import celeryconf as celery_conf
from ..conf.iniconf import settings
from ..common.data import STORED_FILENAME, ORIGINAL_FILENAME
from .storage_manager import StorageSelector, MissingInputsException

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
logging.info("BASE_RUN_DIR: {}".format(settings.get('worker', 'BASE_RUN_DIR', fallback=None)))
logging.info("DISABLE_EXPOSURE_SUMMARY: {}".format(settings.get('worker', 'DISABLE_EXPOSURE_SUMMARY', fallback=False)))


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


# When a worker connects send a task to the worker-monitor to register a new model
@worker_ready.connect
def register_worker(sender, **k):
    m_supplier = os.environ.get('OASIS_MODEL_SUPPLIER_ID')
    m_name = os.environ.get('OASIS_MODEL_ID')
    m_id = os.environ.get('OASIS_MODEL_VERSION_ID')
    m_settings = get_model_settings()
    m_version = get_worker_versions()
    m_conf = get_json(get_oasislmf_config_path(m_id))
    logging.info('register_worker: SUPPLIER_ID={}, MODEL_ID={}, VERSION_ID={}'.format(m_supplier, m_name, m_id))
    logging.info('versions: {}'.format(m_version))
    logging.info('settings: {}'.format(m_settings))
    logging.info('oasislmf config: {}'.format(m_conf))

    signature(
        'run_register_worker',
        args=(m_supplier, m_name, m_id, m_settings, m_version, m_conf),
    ).delay()


class InvalidInputsException(OasisException):
    def __init__(self, input_archive):
        super(InvalidInputsException, self).__init__('Inputs location not a tarfile: {}'.format(input_archive))


class MissingModelDataException(OasisException):
    def __init__(self, model_data_dir):
        super(MissingModelDataException, self).__init__('Model data not found: {}'.format(model_data_dir))


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
        model_id = settings.get('worker', 'model_id', fallback=None)

    if conf_var:
        return conf_var

    if model_id:
        model_root = settings.get('worker', 'model_data_directory', fallback='/var/oasis/')
        model_specific_conf = Path(model_root, '{}-oasislmf.json'.format(model_id))
        if model_specific_conf.exists():
            return str(model_specific_conf)

    return str(Path(model_root, 'oasislmf.json'))


# Send notification back to the API Once task is read from Queue
def notify_api_task_started(analysis_id, task_id, task_slug):
    logging.info("Notify API tasks has started: analysis_id={}, task_id={}, task_slug={}".format(
        analysis_id,
        task_id,
        task_slug,
    ))
    signature(
        'record_sub_task_start',
        kwargs={
            'analysis_id': analysis_id,
            'task_slug': task_slug,
            'task_id': task_id,
        },
    ).delay()


@task(name='run_analysis', bind=True)
def start_analysis_task(self, analysis_id=None, initiator_id=None, input_location=None, analysis_settings_file=None, complex_data_files=None, slug=None):
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
            notify_api_task_started(analysis_id, self.request.id, self.request.delivery_info['routing_key'])
            self.update_state(state=RUNNING_TASK_STATUS)
            output_location, traceback_location, log_location, return_code = start_analysis(
                analysis_settings,
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


    config_path = get_oasislmf_config_path()
    tmp_dir = TemporaryDir(persist=tmpdir_persist, basedir=tmpdir_base)
    filestore.media_root = settings.get('worker', 'MEDIA_ROOT')

    if complex_data_files:
        tmp_input_dir = TemporaryDir(persist=tmpdir_persist, basedir=tmpdir_base)
    else:
        tmp_input_dir = suppress()

    with tmp_dir as run_dir, tmp_input_dir as input_data_dir:

        # Fetch generated inputs
        analysis_settings_file = filestore.get(analysis_settings, run_dir)
        input_archive = filestore.get(input_location, run_dir)
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


@task(name='generate_input', bind=True)
def generate_input(self,
                   analysis_id=None,
                   initiator_id=None,
                   loc_file=None,
                   acc_file=None,
                   info_file=None,
                   scope_file=None,
                   settings_file=None,
                   complex_data_files=None,
                   chunk_index=None,
                   slug=None):
    """Generates the input files for the loss calculation stage.

    This function is a thin wrapper around "oasislmf model generate-oasis-files".
    A temporary directory is created to contain the output oasis files.

    Args:
        analysis_id (int): ID of the analysis.
        loc_file (str): Name of the portfolio locations file.
        acc_file (str): Name of the portfolio accounts file.
        info_file (str): Name of the portfolio reinsurance info file.
        scope_file (str): Name of the portfolio reinsurance scope file.
        settings_file (str): Name of the analysis settings file.
        complex_data_files (list of complex_model_data_file): List of dicts containing
            on-disk and original filenames for required complex model data files.
        chunk_index (int): The index of the chunk to process

    Returns:
        (tuple(str, str)) Paths to the outputs tar file and errors tar file.

    """
    logging.info("args: {}".format(str(locals())))
    logging.info(str(get_worker_versions()))
    notify_api_task_started(analysis_id, self.request.id, f'input-generation-{chunk_index or 0}')

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

        # Store refs
        results = {
            'output_location': output_tar_path,
            'log_location': traceback,
            #'error_location': traceback_fp,
            'return_code': result.returncode,
            'lookup_error_location': lookup_error,
            'lookup_success_location': lookup_success,
            'lookup_validation_location': lookup_validation,
            'summary_levels_location': summary_levels,
            'task_id': self.request.id,
        }
        ## Merge 'Store refs' and ' Store result files' ?
        logging.debug("task_output: {}".format(results))
        return results

#
# input generation tasks
#


@task(bind=True, name='prepare_input_generation_params')
def prepare_input_generation_params(
    self,
    loc_file=None,
    acc_file=None,
    info_file=None,
    scope_file=None,
    settings_file=None,
    complex_data_files=None,
    multiprocessing=False,
    analysis_id=None,
    initiator_id=None,
    slug=None,
):
    logging.info("prepare_input_generation_params: {}".format(str(locals())))
    notify_api_task_started(analysis_id, self.request.id, slug)
    model_id = settings.get('worker', 'model_id')
    config_path = get_oasislmf_config_path(model_id)
    config = get_json(config_path)

    media_root = settings.get('worker', 'MEDIA_ROOT')
    oasis_files_dir = os.path.join(media_root, f'input-generation-oasis-files-dir-{analysis_id}-{uuid.uuid4().hex}')
    Path(oasis_files_dir).mkdir(parents=True, exist_ok=True)

    location_file        = filestore.get(loc_file, oasis_files_dir)
    accounts_file        = filestore.get(acc_file, oasis_files_dir)
    ri_info_file         = filestore.get(info_file, oasis_files_dir)
    ri_scope_file        = filestore.get(scope_file, oasis_files_dir)
    lookup_settings_file = filestore.get(settings_file, oasis_files_dir)

    if complex_data_files:
        input_data_dir = os.path.join(media_root, f'input-generation-input-data-dir-{analysis_id}-{uuid.uuid4().hex}')
        Path(input_data_dir).mkdir(parents=True, exist_ok=True)
    else:
        input_data_dir = None

    if config.get('lookup_config_json'):
        lookup_config_json = os.path.join(
            os.path.dirname(config_path),
            config.get('lookup_config_json'))
    else:
        lookup_config_json = None

    params = OasisManager().prepare_input_generation_params(
        oasis_files_dir,
        location_file,
        lookup_config_fp=lookup_config_json,
        summarise_exposure=not settings.getboolean('worker', 'DISABLE_EXPOSURE_SUMMARY', fallback=False),
        accounts_fp=accounts_file,
        multiprocessing=multiprocessing,
        user_data_dir=input_data_dir,
        complex_lookup_config_fp=lookup_settings_file,
        ri_scope_fp=ri_scope_file,
        ri_info_fp=ri_info_file,
    )
    return params


@task(bind=True, name='prepare_inputs_directory')
def prepare_inputs_directory(self, params, analysis_id=None, initiator_id=None, slug=None):
    notify_api_task_started(analysis_id, self.request.id, slug)
    OasisManager().prepare_input_directory(**params)
    return params


@task(bind=True, name='prepare_keys_file_chunk')
def prepare_keys_file_chunk(self, params, chunk_idx, num_chunks, analysis_id=None, initiator_id=None, slug=None):
    notify_api_task_started(analysis_id, self.request.id, slug)

    chunk_target_dir = os.path.join(params['target_dir'], f'input-generation-chunk-{chunk_idx}')
    Path(chunk_target_dir).mkdir(exist_ok=True, parents=True)
    params['chunk_keys_fp'] = os.path.join(chunk_target_dir, 'keys.csv')
    params['chunk_keys_errors_fp'] = os.path.join(chunk_target_dir, 'keys-errors.csv')

    lookup_config = params['lookup_config']
    if lookup_config and lookup_config['keys_data_path'] in ['.', './']:
        lookup_config['keys_data_path'] = os.path.join(os.path.dirname(params['lookup_config_fp']))
    elif lookup_config and not os.path.isabs(lookup_config['keys_data_path']):
        lookup_config['keys_data_path'] = os.path.join(os.path.dirname(params['lookup_config_fp']), lookup_config['keys_data_path'])

    _, lookup = OasisLookupFactory.create(
        lookup_config=lookup_config,
        model_keys_data_path=params['keys_data_fp'],
        model_version_file_path=params['model_version_fp'],
        lookup_package_path=params['lookup_package_fp'],
        complex_lookup_config_fp=params['complex_lookup_config_fp'],
        user_data_dir=params['user_data_dir'],
        output_directory=chunk_target_dir,
    )
    location_df = OasisLookupFactory.get_exposure(
        lookup=lookup,
        source_exposure_fp=params['exposure_fp'],
    )
    location_df = pd.np.array_split(location_df, num_chunks)[chunk_idx]

    OasisLookupFactory.save_results(
        lookup,
        location_df=location_df,
        successes_fp=params['chunk_keys_fp'],
        errors_fp=params['chunk_keys_errors_fp'],
        multiprocessing=params['multiprocessing'],
    )

    return params


@task(bind=True, name='collect_keys')
def collect_keys(self, chunk_params, analysis_id=None, initiator_id=None, slug=None):
    notify_api_task_started(analysis_id, self.request.id, slug)
    res = {**chunk_params[0]}
    del res['chunk_keys_fp']
    del res['chunk_keys_errors_fp']

    def load_dataframes(paths):
        for p in paths:
            try:
                df = get_dataframe(p)
                yield df
            except OasisException:
                pass

    non_empty_frames = list(load_dataframes(p['chunk_keys_fp'] for p in chunk_params))
    if non_empty_frames:
        keys = pd.concat(non_empty_frames)
        res['keys_fp'] = os.path.join(res['target_dir'], 'keys.csv')
        keys.to_csv(res['keys_fp'], index=False, encoding='utf-8')
    else:
        res['keys_fp'] = None

    non_empty_frames = list(load_dataframes(p['chunk_keys_errors_fp'] for p in chunk_params))
    if non_empty_frames:
        keys_errors = pd.concat(non_empty_frames)
        res['keys_errors_fp'] = os.path.join(res['target_dir'], 'keys-errors.csv')
        keys_errors.to_csv(res['keys_errors_fp'], index=False, encoding='utf-8')
    else:
        res['keys_errors_fp'] = None

    # remove all the chunk directories so that they dont break run directory prep
    for p in glob.glob(os.path.join(res['target_dir'], 'input-generation-chunk-*')):
        shutil.rmtree(p)

    return res


@task(bind=True, name='write_input_files')
def write_input_files(self, params, analysis_id=None, initiator_id=None, slug=None):
    logging.info('write_input_files: analysis_id={}, initiator_id={}, slug={}'.format(
        analysis_id, initiator_id, slug
    ))

    logging.info("args: {}".format({
        'exposure_fp': params['exposure_fp'],
        'accounts_fp': params['accounts_fp'],
        'ri_info_fp': params['ri_info_fp'],
        'ri_scope_fp': params['ri_scope_fp'],
        'target_dir': params['target_dir'],
        'summarise_exposure': params['summarise_exposure'],
        'deterministic': params['deterministic'],
        'keys_fp': params['keys_fp'],
        'keys_errors_fp': params['keys_errors_fp'],
        'group_id_cols': params['group_id_cols'],
        'oasis_files_prefixes': params['oasis_files_prefixes']
    }))

    OasisManager().write_input_files(
        **params
    )

    media_root = settings.get('worker', 'MEDIA_ROOT')

    if params.get('keys_error_fp'):
        hashed_filename = os.path.join(media_root, '{}.csv'.format(uuid.uuid4().hex))
        shutil.copy(params['keys_error_fp'], hashed_filename)
        params['lookup_error_location'] = str(Path(hashed_filename).relative_to(media_root))

    lookup_success_fp = next(iter(glob.glob(os.path.join(params['target_dir'], 'gul_summary_map.csv'))), None)
    if lookup_success_fp:
        hashed_filename = os.path.join(media_root, '{}.csv'.format(uuid.uuid4().hex))
        shutil.copy(lookup_success_fp, hashed_filename)
        params['lookup_success_location'] = str(Path(hashed_filename).relative_to(media_root))

    lookup_validation_fp = next(iter(glob.glob(os.path.join(params['target_dir'], 'exposure_summary_report.json'))), None)
    if lookup_validation_fp:
        hashed_filename = os.path.join(media_root, '{}.json'.format(uuid.uuid4().hex))
        shutil.copy(lookup_validation_fp, hashed_filename)
        params['lookup_validation_location'] = str(Path(hashed_filename).relative_to(media_root))

    summary_levels_fp = next(iter(glob.glob(os.path.join(params['target_dir'], 'exposure_summary_levels.json'))), None)
    if summary_levels_fp:
        hashed_filename = os.path.join(media_root, '{}.json'.format(uuid.uuid4().hex))
        shutil.copy(summary_levels_fp, hashed_filename)
        params['summary_levels_location'] = str(Path(hashed_filename).relative_to(media_root))

    output_tar_name = os.path.join(media_root, '{}.tar.gz'.format(uuid.uuid4().hex))
    output_tar_path = str(Path(output_tar_name).relative_to(media_root))

    logging.info("output_tar_fp: {}".format(output_tar_path))
    logging.info("lookup_error_fp: {}".format(params.get('keys_error_fp')))
    logging.info("lookup_success_fp: {}".format(lookup_success_fp))
    logging.info("lookup_validation_fp: {}".format(lookup_validation_fp))
    logging.info("summary_levels_fp: {}".format(summary_levels_fp))

    params['output_location'] = output_tar_path
    with tarfile.open(output_tar_name, 'w:gz') as tar:
        tar.add(params['target_dir'], arcname='/')

    return params


@task(bind=True, name='cleanup_input_generation')
def cleanup_input_generation(self, params, analysis_id=None, initiator_id=None, slug=None):
    notify_api_task_started(analysis_id, self.request.id, slug)

    if not settings.getboolean('worker', 'KEEP_RUN_DIR', fallback=False):
        shutil.rmtree(params['target_dir'], ignore_errors=True)

        if params['user_data_dir']:
            shutil.rmtree(params['user_data_dir'], ignore_errors=True)

    return params


#
# loss generation tasks
#


@task(bind=True, name='extract_losses_generation_inputs')
def extract_losses_generation_inputs(
    self,
    inputs_location=None,
    complex_data_files=None,
    analysis_id=None,
    initiator_id=None,
    slug=None,
):
    media_root = settings.get('worker', 'MEDIA_ROOT')

    run_dir = os.path.join(media_root, f'loss-generation-oasis-files-dir-{analysis_id}-{uuid.uuid4()}')
    Path(run_dir).mkdir(parents=True, exist_ok=True)

    media_root = settings.get('worker', 'MEDIA_ROOT')
    input_archive = os.path.join(media_root, inputs_location)

    if not os.path.exists(input_archive):
        raise MissingInputsException(input_archive)
    if not tarfile.is_tarfile(input_archive):
        raise InvalidInputsException(input_archive)

    input_data_dir = os.path.join(run_dir, 'input')
    with tarfile.open(input_archive) as f:
        f.extractall(input_data_dir)

    if complex_data_files:
        user_data_dir = os.path.join(media_root, f'loss-generation-oasis-files-dir-{analysis_id}-{uuid.uuid4()}')
        Path(user_data_dir).mkdir(parents=True, exist_ok=True)
        prepare_complex_model_file_inputs(complex_data_files, os.path.join(media_root, user_data_dir))
    else:
        user_data_dir = None

    return run_dir, user_data_dir


@task(bind=True, name='prepare_losses_generation_params')
def prepare_losses_generation_params(
    self,
    run_paths,
    analysis_id=None,
    initiator_id=None,
    analysis_settings_file=None,
    slug=None,
    num_chunks=None,
):
    notify_api_task_started(analysis_id, self.request.id, slug)
    run_path, user_data_dir = run_paths

    media_root = settings.get('worker', 'MEDIA_ROOT')

    model_id = settings.get('worker', 'model_id')
    config_path = get_oasislmf_config_path(model_id)
    config = get_json(config_path)

    oasis_files_dir = os.path.join(run_path, 'input')

    return OasisManager().prepare_loss_generation_params(
        run_path,
        oasis_files_dir,
        os.path.join(media_root, analysis_settings_file),
        os.path.join(os.path.dirname(config_path), config['model_data_dir']),
        user_data_dir=user_data_dir,
        ktools_error_guard=settings.getboolean('worker', 'KTOOLS_ERROR_GUARD', fallback=True),
        ktools_debug=settings.getboolean('worker', 'DEBUG_MODE', fallback=False),
        ktools_fifo_relative=True,
        ktools_alloc_rule_gul=settings.get('worker', 'KTOOLS_ALLOC_RULE_GUL', fallback=None),
        ktools_alloc_rule_il=settings.get('worker', 'KTOOLS_ALLOC_RULE_IL', fallback=None),
        ktools_alloc_rule_ri=settings.get('worker', 'KTOOLS_ALLOC_RULE_RI', fallback=None),
        ktools_num_processes=num_chunks,
    )


@task(bind=True, name='prepare_losses_generation_directory')
def prepare_losses_generation_directory(self, params, analysis_id=None, initiator_id=None, slug=None):
    notify_api_task_started(analysis_id, self.request.id, slug)

    params['analysis_settings'] = OasisManager().prepare_run_directory(**params)

    return params


@task(bind=True, name='generate_losses_chunk')
def generate_losses_chunk(self, params, chunk_idx, num_chunks, analysis_id=None, initiator_id=None, slug=None):
    notify_api_task_started(analysis_id, self.request.id, slug)

    chunk_params = {**params, 'script_fp': f'{params["script_fp"]}.{chunk_idx}'}

    params['fifo_queue_dir'], params['bash_trace'] = OasisManager().run_loss_generation(**chunk_params)

    return {
        **params,
        'chunk_script_path': chunk_params['script_fp'],
        'process_number': chunk_idx + 1,
    }


@task(bind=True, name='generate_losses_output')
def generate_losses_output(self, params, analysis_id=None, initiator_id=None, slug=None):
    notify_api_task_started(analysis_id, self.request.id, slug)
    res = {**params[0]}

    OasisManager().run_loss_outputs(**res)
    res['bash_trace'] = '\n\n'.join(
        f'Analysis Chunk {idx}:\n{chunk["bash_trace"]}' for idx, chunk in enumerate(params)
    )

    return params[0]


@task(bind=True, name='cleanup_losses_generation')
def cleanup_losses_generation(self, params, analysis_id=None, initiator_id=None, slug=None):
    notify_api_task_started(analysis_id, self.request.id, slug)

    if not settings.getboolean('worker', 'KEEP_RUN_DIR', fallback=False):
        shutil.rmtree(params['model_run_fp'], ignore_errors=True)

        if params['user_data_dir']:
            shutil.rmtree(params['user_data_dir'], ignore_errors=True)

    return params


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
            os.symlink(from_path, to_path)


@before_task_publish.connect
def mark_task_as_queued_receiver(*args, headers=None, body=None, **kwargs):
    """
    This receiver is replicated on the server side as it needs to be called from the
    queueing thread to be triggered
    """
    analysis_id = body[1].get('analysis_id')
    slug = body[1].get('slug')

    if analysis_id and slug:
        signature('mark_task_as_queued').delay(analysis_id, slug, headers['id'], datetime.now().timestamp())
