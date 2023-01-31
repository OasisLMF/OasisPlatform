from __future__ import absolute_import

import glob
import json
import logging
import os
import pathlib
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from datetime import datetime

import fasteners
import filelock
import pandas as pd
from billiard.exceptions import WorkerLostError
from celery import Celery, signature
from celery.signals import (before_task_publish, task_failure, task_revoked,
                            worker_ready)
from natsort import natsorted
from oasislmf import __version__ as mdk_version
from oasislmf.manager import OasisManager
from oasislmf.model_preparation.lookup import OasisLookupFactory
from oasislmf.utils.data import get_json
from oasislmf.utils.exceptions import OasisException
from oasislmf.utils.status import OASIS_TASK_STATUS
from pathlib2 import Path

from ..common.data import ORIGINAL_FILENAME, STORED_FILENAME
from ..conf import celeryconf as celery_conf
from ..conf.iniconf import settings
from .backends.aws_storage import AwsObjectStore
from .backends.azure_storage import AzureObjectStore
from .storage_manager import BaseStorageConnector

'''
Celery task wrapper for Oasis ktools calculation.
'''

LOG_FILE_SUFFIX = 'txt'
ARCHIVE_FILE_SUFFIX = 'tar.gz'
RUNNING_TASK_STATUS = OASIS_TASK_STATUS["running"]["id"]
TASK_LOG_DIR = settings.get('worker', 'TASK_LOG_DIR', fallback='/var/log/oasis/tasks')

app = Celery()
app.config_from_object(celery_conf)

logging.info("Started worker")
debug_worker = settings.getboolean('worker', 'DEBUG', fallback=False)

# Quiet sub-loggers
logging.getLogger('billiard').setLevel('INFO')
#logging.getLogger('importlib').setLevel('INFO')
#logging.getLogger('pandas').setLevel('INFO')


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


class LoggingTaskContext:
    """ Adds a file log handler to the root logger and pushes a copy all logs to
        the 'log_filename'

        Docs: https://docs.python.org/3/howto/logging-cookbook.html#using-a-context-manager-for-selective-logging
    """
    def __init__(self, logger, log_filename, level=None, close=True):
        self.logger = logger
        self.level = level
        self.log_filename = log_filename
        self.close = close
        self.handler = logging.FileHandler(log_filename)

    def __enter__(self):
        if self.level:
            self.handler.setLevel(self.level)
        if self.handler:
            self.logger.addHandler(self.handler)

    def __exit__(self, et, ev, tb):
        if self.handler:
            self.logger.removeHandler(self.handler)
        if self.handler and self.close:
            self.handler.close()


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


def merge_dirs(src_root, dst_root):
    for root, dirs, files in os.walk(src_root):
        for f in files:
            src = os.path.join(root, f)
            rel_dst = os.path.relpath(src, src_root)
            abs_dst = os.path.join(dst_root, rel_dst)
            Path(abs_dst).parent.mkdir(exist_ok=True, parents=True)
            shutil.copy(os.path.join(root, f), abs_dst)


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


def notify_api_status(analysis_pk, task_status):
    logging.info("Notify API: analysis_id={}, status={}".format(
        analysis_pk,
        task_status
    ))
    signature(
        'set_task_status',
        args=(analysis_pk, task_status, datetime.now().timestamp()),
        queue='celery'
    ).delay()



#https://docs.celeryproject.org/en/latest/userguide/signals.html#task-revoked
@task_revoked.connect
def revoked_handler(*args, **kwargs):
    # Break the chain
    request = kwargs.get('request')
    request.chain[:] = []



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

    # Check for 'DISABLE_WORKER_REG' before se:NERDTreeToggle
    # unding task to API
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
    logging.info("KEEP_LOCAL_DATA: {}".format(settings.get('worker', 'KEEP_LOCAL_DATA', fallback='False')))
    logging.info("KEEP_REMOTE_DATA: {}".format(settings.get('worker', 'KEEP_REMOTE_DATA', fallback='False')))
    logging.info("BASE_RUN_DIR: {}".format(settings.get('worker', 'BASE_RUN_DIR', fallback='None')))
    logging.info("OASISLMF_CONFIG: {}".format(settings.get('worker', 'oasislmf_config', fallback='None')))
    logging.info("TASK_LOG_DIR: {}".format(settings.get('worker', 'TASK_LOG_DIR', fallback='/var/log/oasis/tasks')))

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
            'dt': datetime.now().timestamp(),
        },
    ).delay()

def update_all_tasks_ids(task_request):
    """ Extract other task_id's from the celery request chain.
        These are sent back to the `worker-monitor` container
        and used to update the AnalysisTaskStatus Objects in the
        Django DB.

        This is so that when a cancellation request is send there are
        stored sub-task id's to revoke
    """
    try:
        task_request.chain.sort()
    except TypeError:
        logging.debug('Task chain header is already sorted')
    chain_tasks = task_request.chain[0]
    task_update_list = list()

    # Sequential tasks - in the celery task chain, important for stopping stalls on a cancellation request
    seq = {t['options']['task_id']:t['kwargs'] for t in chain_tasks['kwargs']['body']['kwargs']['tasks']}
    for task_id in seq:
        task_update_list.append((task_id, seq[task_id]['analysis_id'], seq[task_id]['slug']))

    # Chunked tasks - This call might get heavy as the chunk load increases (possibly remove later)
    chunks = {t['options']['task_id']:t['kwargs'] for t in chain_tasks['kwargs']['header']['kwargs']['tasks']}
    for task_id in chunks:
        task_update_list.append((task_id, chunks[task_id]['analysis_id'], chunks[task_id]['slug']))
    signature('update_task_id').delay(task_update_list)



# --- input generation tasks ------------------------------------------------ #

def keys_generation_task(fn):
    def maybe_prepare_complex_data_files(complex_data_files, user_data_dir):
        with filelock.FileLock(f'{user_data_dir}.lock'):
            if complex_data_files:
                user_data_path = Path(user_data_dir)
                if not user_data_path.exists():
                    user_data_path.mkdir(parents=True, exist_ok=True)
                    prepare_complex_model_file_inputs(complex_data_files, str(user_data_path))
        try:
            os.remove('{user_data_dir}.lock')
        except OSError:
            logging.info(f'Failed to remove {user_data_dir}.lock')

    def maybe_fetch_file(datafile, filepath, subdir=''):
        with filelock.FileLock(f'{filepath}.lock'):
            if not Path(filepath).exists():
                logging.info(f'file: {datafile}')
                logging.info(f'filepath: {filepath}')
                filestore.get(datafile, filepath, subdir)
        try:
            os.remove(f'{filepath}.lock')
        except OSError:
            logging.info(f'Failed to remove {filepath}.lock')


    def get_file_ref(kwargs, params, arg_name):
        """ Either fetch file ref from Kwargs or override from pre-analysis hook
        """
        file_from_server = kwargs.get(arg_name)
        file_from_hook = params.get(f'pre_{arg_name}')
        if not file_from_server:
            logging.info(f'{arg_name}: (Not loaded)')
            return None
        elif file_from_hook:
            logging.info(f'{arg_name}: {file_from_hook} (pre-analysis-hook)')
            return file_from_hook
        logging.info(f'{arg_name}: {file_from_server} (portfolio)')
        return file_from_server


    def log_task_entry(slug, request_id, analysis_id):
        if slug:
            logging.info('\n')
            logging.info(f'====== {slug} '.ljust(90, '='))
        notify_api_task_started(analysis_id, request_id, slug)

    def log_params(params, kwargs):
        exclude_keys = [
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
        ]
        if isinstance(params, list):
            params = params[0]
        print_params = {k: params[k] for k in set(list(params.keys())) - set(exclude_keys)}
        if debug_worker:
            logging.info('keys_generation_task: \nparams={}, \nkwargs={}'.format(
                json.dumps(print_params, indent=2),
                json.dumps(kwargs, indent=2),
            ))

    def _prepare_directories(params, analysis_id, run_data_uuid, kwargs):
        params['storage_subdir'] = f'analysis-{analysis_id}_files-{run_data_uuid}'
        params['root_run_dir'] = os.path.join(settings.get('worker', 'base_run_dir', fallback='/tmp/run'), params['storage_subdir'])
        Path(params['root_run_dir']).mkdir(parents=True, exist_ok=True)

        # Set `oasis-file-generation` input files
        params.setdefault('target_dir', params['root_run_dir'])
        params.setdefault('user_data_dir', os.path.join(params['root_run_dir'], f'user-data'))
        params.setdefault('lookup_complex_config_json', os.path.join(params['root_run_dir'], 'analysis_settings.json'))

        # Generate keys files
        params.setdefault('keys_fp', os.path.join(params['root_run_dir'], 'keys.csv'))
        params.setdefault('keys_errors_fp', os.path.join(params['root_run_dir'], 'keys-errors.csv'))

        # user settings and data
        settings_file = kwargs.get('analysis_settings_file')
        complex_data_files = kwargs.get('complex_data_files')

        # Load OED file references (filenames or object keys)
        loc_file = get_file_ref(kwargs, params, 'loc_file')
        acc_file = get_file_ref(kwargs, params, 'acc_file')
        info_file = get_file_ref(kwargs, params, 'info_file')
        scope_file = get_file_ref(kwargs, params, 'scope_file')

        # Prepare 'generate-oasis-files' input files
        if loc_file:
            loc_extention = "".join(pathlib.Path(loc_file).suffixes)
            loc_subdir = params.get('storage_subdir','') if params.get('pre_loc_file') else ''
            params['oed_location_csv'] = os.path.join(params['root_run_dir'], f'location{loc_extention}')
            maybe_fetch_file(loc_file, params['oed_location_csv'], loc_subdir)
        if acc_file:
            acc_extention = "".join(pathlib.Path(acc_file).suffixes)
            acc_subdir = params.get('storage_subdir','') if params.get('pre_acc_file') else ''
            params['oed_accounts_csv'] = os.path.join(params['root_run_dir'], f'account{acc_extention}')
            maybe_fetch_file(acc_file, params['oed_accounts_csv'], acc_subdir)
        if info_file:
            info_extention = "".join(pathlib.Path(info_file).suffixes)
            info_subdir = params.get('storage_subdir','') if params.get('pre_info_file') else ''
            params['oed_info_csv'] = os.path.join(params['root_run_dir'], f'reinsinfo{info_extention}')
            maybe_fetch_file(info_file, params['oed_info_csv'], info_subdir)
        if scope_file:
            scope_extention = "".join(pathlib.Path(scope_file).suffixes)
            scope_subdir = params.get('storage_subdir','') if params.get('pre_scope_file') else ''
            params['oed_scope_csv'] = os.path.join(params['root_run_dir'], f'reinsscope{scope_extention}')
            maybe_fetch_file(scope_file, params['oed_scope_csv'], scope_subdir)

        if settings_file:
            maybe_fetch_file(settings_file, params['lookup_complex_config_json'])
        if complex_data_files:
            maybe_prepare_complex_data_files(complex_data_files, params['user_data_dir'])
        else:
            params['user_data_dir'] = None


    def run(self, params, *args, run_data_uuid=None, analysis_id=None, **kwargs):
        kwargs['log_filename'] = os.path.join(TASK_LOG_DIR, f"{run_data_uuid}_{kwargs.get('slug')}.log")
        with LoggingTaskContext(logging.getLogger(), log_filename=kwargs['log_filename']):
            log_task_entry(kwargs.get('slug'), self.request.id, analysis_id)

            if isinstance(params, list):
                for p in params:
                    _prepare_directories(p, analysis_id, run_data_uuid, kwargs)
            else:
                _prepare_directories(params, analysis_id, run_data_uuid, kwargs)

            log_params(params, kwargs)
            return fn(self, params, *args, analysis_id=analysis_id, run_data_uuid=run_data_uuid, **kwargs)

    return run


@app.task(bind=True, name='prepare_input_generation_params', **celery_conf.worker_task_kwargs)
@keys_generation_task
def prepare_input_generation_params(
    self,
    params,
    loc_file=None,
    acc_file=None,
    info_file=None,
    scope_file=None,
    settings_file=None,
    complex_data_files=None,
    multiprocessing=False,
    run_data_uuid=None,
    analysis_id=None,
    initiator_id=None,
    slug=None,
    **kwargs,
):
    notify_api_status(analysis_id, 'INPUTS_GENERATION_STARTED')
    update_all_tasks_ids(self.request) # updates all the assigned task_ids

    model_id = settings.get('worker', 'model_id')
    config_path = get_oasislmf_config_path(model_id)
    config = get_json(config_path)
    lookup_params = {**{k:v for k,v in config.items() if not k.startswith('oed_')}, **params}

    # convert relative paths to Aboslute
    lookup_path_vars = [
        'lookup_data_dir',
        'lookup_config_json',
        'model_version_csv',
        'lookup_module_path',
        'model_settings_json',
        'exposure_pre_analysis_module',
        'exposure_pre_analysis_setting_json',
    ]
    for path_val in lookup_path_vars:
        if lookup_params.get(path_val, False):
            if not os.path.isabs(lookup_params[path_val]):
                abs_path_val = os.path.join(
                    os.path.dirname(config_path),
                    lookup_params[path_val]
                )
                lookup_params[path_val] = abs_path_val

    gen_files_params = OasisManager()._params_generate_files(**lookup_params)
    pre_hook_params = OasisManager()._params_exposure_pre_analysis(**lookup_params)
    params = {**gen_files_params, **pre_hook_params}

    params['log_location'] = filestore.put(kwargs.get('log_filename'))
    params['verbose'] = debug_worker
    return params


@app.task(bind=True, name='pre_analysis_hook', **celery_conf.worker_task_kwargs)
@keys_generation_task
def pre_analysis_hook(self,
    params,
    run_data_uuid=None,
    analysis_id=None,
    initiator_id=None,
    slug=None,
    **kwargs
):
    if params.get('exposure_pre_analysis_module'):
        with TemporaryDir() as hook_target_dir:
            params['oasis_files_dir'] = hook_target_dir
            pre_hook_output = OasisManager().exposure_pre_analysis(**params)
            files_modified = pre_hook_output.get('modified', {})

            # store updated files
            params['pre_loc_file']   = filestore.put(files_modified.get('oed_location_csv'), subdir=params['storage_subdir'])
            params['pre_acc_file']   = filestore.put(files_modified.get('oed_accounts_csv'), subdir=params['storage_subdir'])
            params['pre_info_file']  = filestore.put(files_modified.get('oed_info_csv'), subdir=params['storage_subdir'])
            params['pre_scope_file'] = filestore.put(files_modified.get('oed_scope_csv'), subdir=params['storage_subdir'])

        # remove any pre-loaded files (only affects this worker)
        oed_files = {v for k,v in params.items() if k.startswith('oed_') and isinstance(v, str)}
        for filepath in oed_files:
            if Path(filepath).exists():
                os.remove(filepath)
    else:
        logging.info('pre_analysis_hook: SKIPPING, param "exposure_pre_analysis_module" not set')
    params['log_location'] = filestore.put(kwargs.get('log_filename'))
    return params


@app.task(bind=True, name='prepare_keys_file_chunk', **celery_conf.worker_task_kwargs)
@keys_generation_task
def prepare_keys_file_chunk(
    self,
    params,
    chunk_idx,
    num_chunks,
    run_data_uuid=None,
    analysis_id=None,
    initiator_id=None,
    slug=None,
    **kwargs
):
    with TemporaryDir() as chunk_target_dir:
        chunk_target_dir = os.path.join(chunk_target_dir, f'lookup-{chunk_idx+1}')
        Path(chunk_target_dir).mkdir(parents=True, exist_ok=True)

        chunk_target_dir = os.path.join(chunk_target_dir, f'lookup-{chunk_idx+1}')
        Path(chunk_target_dir).mkdir(parents=True, exist_ok=True)

        _, lookup = OasisLookupFactory.create(
            lookup_config_fp=params['lookup_config_json'],
            model_keys_data_path=params['lookup_data_dir'],
            model_version_file_path=params['model_version_csv'],
            lookup_module_path=params['lookup_module_path'],
            complex_lookup_config_fp=params['lookup_complex_config_json'],
            user_data_dir=params['user_data_dir'],
            output_directory=chunk_target_dir,
        )

        location_df = lookup.get_locations(location_fp=params['oed_location_csv'])
        location_df = pd.np.array_split(location_df, num_chunks)[chunk_idx]
        chunk_keys_fp = os.path.join(chunk_target_dir, 'keys.csv')
        chunk_keys_errors_fp = os.path.join(chunk_target_dir, 'keys-errors.csv')
        lookup.generate_key_files(
            location_fp=None,
            location_df=location_df,
            successes_fp=chunk_keys_fp,
            errors_fp=chunk_keys_errors_fp,
            output_format='oasis',
            keys_success_msg=False,
            multiproc_enabled=params.get('lookup_multiprocessing', False),
            multiproc_num_cores=params.get('lookup_num_processes', -1),
            multiproc_num_partitions=params.get('lookup_num_chunks', -1),
        )

        # Store chunks
        storage_subdir = f'{run_data_uuid}/oasis-files'
        params['chunk_keys'] = filestore.put(
            chunk_target_dir,
            filename=f'lookup-{chunk_idx+1}.tar.gz',
            subdir=params['storage_subdir']
        )

    params['log_location'] = filestore.put(kwargs.get('log_filename'))
    return params


@app.task(bind=True, name='collect_keys', **celery_conf.worker_task_kwargs)
@keys_generation_task
def collect_keys(
    self,
    params,
    run_data_uuid=None,
    analysis_id=None,
    initiator_id=None,
    slug=None,
    **kwargs
 ):
    # Setup return params
    chunk_params = {**params[0]}
    storage_subdir = chunk_params['storage_subdir']
    del chunk_params['chunk_keys']

    def merge_dataframes(paths, output_file, file_type, unique=True):
        pd_read_func = getattr(pd, f"read_{file_type}")
        if not paths:
            logging.warning("merge_dataframes was called with an empty path list.")
            return
        df_chunks = []
        for path in paths:
            try:
                df_chunks.append(pd_read_func(path))
            except pd.errors.EmptyDataError:
                # Ignore empty files.
                logging.info(f"File {path} is empty. --skipped--")

        if not df_chunks:
            logging.warning(f"All files were empty: {paths}. --skipped--")
            return
        # add opt for Select merge strat
        df = pd.concat(df_chunks)

        if unique:
            df = df[~df.index.duplicated(keep='first')]
        pd_write_func = getattr(df, f"to_{file_type}")
        pd_write_func(output_file, index=True)

    def take_first(paths, output_file):
        first_path = paths[0]
        logging.info(f"Using {first_path} and ignoring others.")
        shutil.copy2(first_path, output_file)

    # Collect files and tar here from chunk_params['target_dir']
    with TemporaryDir() as chunks_dir:
        # extract chunks
        chunk_tars = [d['chunk_keys'] for d in params]
        for tar in chunk_tars:
            extract_to = os.path.join(chunks_dir, os.path.basename(tar).split('.')[0])
            filestore.extract(tar, extract_to, storage_subdir)

        file_paths = glob.glob(chunks_dir + '/lookup-[0-9]*/*') # paths for every file to merge  (inputs for merge)
        file_names = set([ os.path.basename(f) for f in file_paths])            # unqiue filenames (output merged results)

        with TemporaryDir() as merge_dir:
            for file in file_names:
                logging.info(f'Merging into file: "{file}"')

                file_type = Path(file).suffix[1:]
                file_name = Path(file).stem
                file_chunks = [f for f in file_paths if f.endswith(file)]
                file_merged = os.path.join(merge_dir, file)
                file_chunks = natsorted(file_chunks)
                #file_unique_rows = True if file == 'ensemble_mapping.csv' else False

                if file_type == 'csv':
                    merge_dataframes(file_chunks, file_merged, file_type)
                elif file_type == 'parquet':
                    merge_dataframes(file_chunks, file_merged, file_type)
                elif file_name in ['events', 'occurrence']:
                    take_first(file_chunks, file_merged)
                else:
                    logging.info(f'No merge method for file: "{file}" --skipped--')

            # store keys data
            chunk_params['keys_data'] = filestore.put(
                merge_dir,
                filename=f'keys-data.tar.gz',
                subdir=chunk_params['storage_subdir']
            )

    chunk_params['log_location'] = filestore.put(kwargs.get('log_filename'))
    return chunk_params


@app.task(bind=True, name='write_input_files', **celery_conf.worker_task_kwargs)
@keys_generation_task
def write_input_files(self, params, run_data_uuid=None, analysis_id=None, initiator_id=None, slug=None, **kwargs):
    # Load Collected keys data
    filestore.extract(params['keys_data'], params['target_dir'], params['storage_subdir'])
    params['keys_data_csv'] = os.path.join(params['target_dir'], 'keys.csv')
    params['keys_errors_csv'] = os.path.join(params['target_dir'], 'keys-errors.csv')
    params['oasis_files_dir'] = params['target_dir']
    OasisManager().generate_files(**params)

    return {
        'lookup_error_location': filestore.put(os.path.join(params['target_dir'], 'keys-errors.csv')),
        'lookup_success_location': filestore.put(os.path.join(params['target_dir'], 'gul_summary_map.csv')),
        'lookup_validation_location': filestore.put(os.path.join(params['target_dir'], 'exposure_summary_report.json')),
        'summary_levels_location': filestore.put(os.path.join(params['target_dir'], 'exposure_summary_levels.json')),
        'output_location': filestore.put(params['target_dir']),
        'log_location': filestore.put(kwargs.get('log_filename')),
    }


@app.task(bind=True, name='cleanup_input_generation', **celery_conf.worker_task_kwargs)
@keys_generation_task
def cleanup_input_generation(self, params, analysis_id=None, initiator_id=None, run_data_uuid=None, slug=None, **kwargs):

    # check for pre-analysis files and remove

    if not settings.getboolean('worker', 'KEEP_LOCAL_DATA', fallback=False):
        # Delete local copy of run data
        shutil.rmtree(params['target_dir'], ignore_errors=True)
    if not settings.getboolean('worker', 'KEEP_REMOTE_DATA', fallback=False):
        # Delete remote copy of run data
        filestore.delete_dir(params['storage_subdir'])
        # Delete pre-analysis files
        if params.get('pre_loc_file'):
            filestore.delete_file(params.get('pre_loc_file'))
        if params.get('pre_acc_file'):
            filestore.delete_file(params.get('pre_acc_file'))
        if params.get('pre_info_file'):
            filestore.delete_file(params.get('pre_info_file'))
        if params.get('pre_scope_file'):
            filestore.delete_file(params.get('pre_scope_file'))

    params['log_location'] = filestore.put(kwargs.get('log_filename'))
    return params



# --- loss generation tasks ------------------------------------------------ #


def loss_generation_task(fn):
    def maybe_extract_tar(filestore_ref, dst, storage_subdir=''):
        logging.info(f'filestore_ref: {filestore_ref}')
        logging.info(f'dst: {dst}')
        with filelock.FileLock(f'{dst}.lock'):
            if not Path(dst).exists():
                filestore.extract(filestore_ref, dst, storage_subdir)

    def maybe_prepare_complex_data_files(complex_data_files, user_data_dir):
        with filelock.FileLock(f'{user_data_dir}.lock'):
            if complex_data_files:
                user_data_path = Path(user_data_dir)
                if not user_data_path.exists():
                    user_data_path.mkdir(parents=True, exist_ok=True)
                    prepare_complex_model_file_inputs(complex_data_files, str(user_data_path))
        try:
            os.remove(f'{user_data_dir}.lock')
        except OSError:
            logging.info(f'Failed to remove {user_data_dir}.lock')

    def maybe_fetch_analysis_settings(analysis_settings_file, analysis_settings_fp):
        with filelock.FileLock(f'{analysis_settings_fp}.lock'):
            if not Path(analysis_settings_fp).exists():
                logging.info(f'analysis_settings_file: {analysis_settings_file}')
                logging.info(f'analysis_settings_fp: {analysis_settings_fp}')
                filestore.get(analysis_settings_file, analysis_settings_fp)
        try:
            os.remove(f'{analysis_settings_fp}.lock')
        except OSError:
            logging.info(f'Failed to remove {analysis_settings_fp}.lock')

    def log_task_entry(slug, request_id, analysis_id):
        if slug:
            logging.info('\n')
            logging.info(f'====== {slug} '.ljust(90, '='))
        notify_api_task_started(analysis_id, request_id, slug)

    def log_params(params, kwargs):
        exclude_keys = []

        if isinstance(params, list):
            params = params[0]
        print_params = {k: params[k] for k in set(list(params.keys())) - set(exclude_keys)}
        if debug_worker:
            logging.info('loss_generation_task: \nparams={}, \nkwargs={}'.format(
                json.dumps(print_params, indent=4),
                json.dumps(kwargs, indent=4),
            ))

    def _prepare_directories(params, analysis_id, run_data_uuid, kwargs):
        print(json.dumps(params, indent=4))

        params['storage_subdir'] = f'analysis-{analysis_id}_losses-{run_data_uuid}'
        params['root_run_dir'] = os.path.join(settings.get('worker', 'base_run_dir', fallback='/tmp/run'), params['storage_subdir'])
        Path(params['root_run_dir']).mkdir(parents=True, exist_ok=True)

        params.setdefault('oasis_files_dir', os.path.join(params['root_run_dir'], f'input-data'))
        params.setdefault('model_run_dir', os.path.join(params['root_run_dir'], f'run-data'))
        params.setdefault('results_path', os.path.join(params['root_run_dir'], f'results-data'))
        params.setdefault('user_data_dir', os.path.join(params['root_run_dir'], f'user-data'))
        params.setdefault('analysis_settings_json', os.path.join(params['root_run_dir'], 'analysis_settings.json'))

        input_location = kwargs.get('input_location')
        if input_location:
            maybe_extract_tar(
                input_location,
                params['oasis_files_dir'],
            )

        run_location = params.get('run_location')
        if run_location:
            maybe_extract_tar(
                run_location,
                params['model_run_dir'],
                params['storage_subdir'],
            )

        complex_data_files = kwargs.get('complex_data_files')
        if complex_data_files:
            maybe_prepare_complex_data_files(
                complex_data_files,
                params['user_data_dir'],
            )

        analysis_settings_file = kwargs.get('analysis_settings_file')
        if analysis_settings_file:
            maybe_fetch_analysis_settings(
                analysis_settings_file,
                params['analysis_settings_json']
            )

    def run(self, params, *args, run_data_uuid=None, analysis_id=None, **kwargs):
        kwargs['log_filename'] = os.path.join(TASK_LOG_DIR, f"{run_data_uuid}_{kwargs.get('slug')}.log")
        with LoggingTaskContext(logging.getLogger(), log_filename=kwargs['log_filename']):
            log_task_entry(kwargs.get('slug'), self.request.id, analysis_id)
            if isinstance(params, list):
                for p in params:
                    _prepare_directories(p, analysis_id, run_data_uuid, kwargs)
            else:
                _prepare_directories(params, analysis_id, run_data_uuid, kwargs)

            log_params(params, kwargs)
            return fn(self, params, *args, analysis_id=analysis_id, **kwargs)

    return run


@app.task(bind=True, name='prepare_losses_generation_params', **celery_conf.worker_task_kwargs)
@loss_generation_task
def prepare_losses_generation_params(
    self,
    params,
    analysis_id=None,
    slug=None,
    num_chunks=None,
    **kwargs,
):
    notify_api_status(analysis_id, 'RUN_STARTED')
    update_all_tasks_ids(self.request) # updates all the assigned task_ids

    model_id = settings.get('worker', 'model_id')
    config_path = get_oasislmf_config_path(model_id)
    config = get_json(config_path)
    run_params = {**config, **params}

    loss_path_vars = [
        'model_data_dir',
        'model_settings_json',
    ]

    for path_val in loss_path_vars:
        if run_params.get(path_val, False):
            if not os.path.isabs(run_params[path_val]):
                abs_path_val = os.path.join(
                    os.path.dirname(config_path),
                    run_params[path_val]
                )
                run_params[path_val] = abs_path_val
        else:
            run_params[path_val] = None

    params = OasisManager()._params_generate_losses(**run_params)
    params['log_location'] = filestore.put(kwargs.get('log_filename'))
    params['verbose'] = debug_worker
    return params


@app.task(bind=True, name='prepare_losses_generation_directory', **celery_conf.worker_task_kwargs)
@loss_generation_task
def prepare_losses_generation_directory(self, params, analysis_id=None, slug=None, **kwargs):
    params['analysis_settings'] = OasisManager().generate_losses_dir(**params)
    params['run_location'] = filestore.put(
        params['model_run_dir'],
        filename='run_directory.tar.gz',
        subdir=params['storage_subdir']
    )
    params['log_location'] = filestore.put(kwargs.get('log_filename'))
    return params


@app.task(bind=True, name='generate_losses_chunk', **celery_conf.worker_task_kwargs)
@loss_generation_task
def generate_losses_chunk(self, params, chunk_idx, num_chunks, analysis_id=None, slug=None, **kwargs):

    if num_chunks == 1:
        # Run multiple ktools pipes (based on cpu cores)
        current_chunk_id = None
        max_chunk_id = -1
        work_dir = 'work'

    else:
        # Run a single ktools pipe
        current_chunk_id = chunk_idx + 1
        max_chunk_id = num_chunks
        work_dir = f'{current_chunk_id}.work'

    chunk_params = {
        **params,
        'process_number': current_chunk_id,
        'max_process_id' : max_chunk_id,
        'ktools_fifo_relative': True,
        'ktools_work_dir': os.path.join(params['model_run_dir'], work_dir),
    }
    Path(chunk_params['ktools_work_dir']).mkdir(parents=True, exist_ok=True)
    OasisManager().generate_losses_partial(**chunk_params)

    return {
        **params,
        'chunk_work_location': filestore.put(
            chunk_params['ktools_work_dir'],
            filename=f'work-{chunk_idx+1}.tar.gz',
            subdir=params['storage_subdir']
        ),
        'ktools_work_dir': chunk_params['ktools_work_dir'],
        'process_number': chunk_idx + 1,
        'max_process_id': max_chunk_id,
        'log_location': filestore.put(kwargs.get('log_filename')),
    }


@app.task(bind=True, name='generate_losses_output', **celery_conf.worker_task_kwargs)
@loss_generation_task
def generate_losses_output(self, params, analysis_id=None, slug=None, **kwargs):
    res = {**params[0]}
    res['max_process_id'] = len(params)

    abs_work_dir = os.path.join(res['model_run_dir'], 'work')
    Path(abs_work_dir).mkdir(exist_ok=True, parents=True)

    # collect the run results
    for p in params:
        with TemporaryDir() as d:
            filestore.extract(p['chunk_work_location'], d, p['storage_subdir'])
            merge_dirs(d, abs_work_dir)

    OasisManager().generate_losses_output(**res)
    res['bash_trace'] = ""

    return {
        **res,
        'output_location': filestore.put(os.path.join(res['model_run_dir'], 'output'), arcname='output'),
        'log_location': filestore.put(kwargs.get('log_filename')),
    }


@app.task(bind=True, name='cleanup_losses_generation', **celery_conf.worker_task_kwargs)
@loss_generation_task
def cleanup_losses_generation(self, params, analysis_id=None, slug=None, **kwargs):
    if not settings.getboolean('worker', 'KEEP_LOCAL_DATA', fallback=False):
        # Delete local copy of run data
        shutil.rmtree(params['root_run_dir'], ignore_errors=True)
    if not settings.getboolean('worker', 'KEEP_REMOTE_DATA', fallback=False):
        # Delete remote copy of run data
        filestore.delete_dir(params['storage_subdir'])
    params['log_location'] = filestore.put(kwargs.get('log_filename'))
    return params


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
        elif filestore._is_locally_stored(stored_fn):
            # If refrence is local filepath check that it exisits and copy/symlink
            from_path = filestore.get(stored_fn)
            to_path = os.path.join(run_directory, orig_fn)
            if os.name == 'nt':
                shutil.copy(from_path, to_path)
            else:
                os.symlink(from_path, to_path)
        else:
            os.symlink(from_path, to_path)

@task_failure.connect
def handle_task_failure(*args, sender=None, task_id=None, **kwargs):
    logging.info("Task error handler")
    task_params = kwargs.get('args')[0]
    task_args = sender.request.kwargs

    # Store output log
    task_log_file = f"{TASK_LOG_DIR}/{task_args.get('run_data_uuid')}_{task_args.get('slug')}.log"
    if os.path.isfile(task_log_file):
        signature('subtask_error_log').delay(
            task_args.get('analysis_id'),
            task_args.get('initiator_id'),
            task_args.get('slug'),
            task_id,
            filestore.put(task_log_file)
        )

    # Wipe worker's remote data storage
    keep_remote_data = settings.getboolean('worker', 'KEEP_REMOTE_DATA', fallback=False)
    dir_remote_data = task_params.get('storage_subdir')
    if not keep_remote_data:
        logging.info(f"deleting remote data, {dir_remote_data}")
        filestore.delete_dir(dir_remote_data)


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
