from __future__ import absolute_import

import glob
import json
import logging
import os
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
from celery.signals import worker_ready, before_task_publish, task_revoked
from oasislmf import __version__ as mdk_version
from oasislmf.manager import OasisManager
from oasislmf.model_preparation.lookup import OasisLookupFactory
from oasislmf.utils.data import get_json
from oasislmf.utils.exceptions import OasisException
from oasislmf.utils.status import OASIS_TASK_STATUS
from pathlib2 import Path

from .storage_manager import StorageSelector
from ..common.data import STORED_FILENAME, ORIGINAL_FILENAME
from ..conf import celeryconf as celery_conf
from ..conf.iniconf import settings

'''
Celery task wrapper for Oasis ktools calculation.
'''

LOG_FILE_SUFFIX = 'txt'
ARCHIVE_FILE_SUFFIX = 'tar.gz'
RUNNING_TASK_STATUS = OASIS_TASK_STATUS["running"]["id"]
app = Celery()
app.config_from_object(celery_conf)

logging.info("Started worker")
filestore = StorageSelector(settings)
debug_worker = settings.getboolean('worker', 'DEBUG', fallback=False)



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

    def maybe_fetch_file(datafile, filepath):
        with filelock.FileLock(f'{filepath}.lock'):
            if not Path(filepath).exists():
                logging.info(f'file: {datafile}')
                logging.info(f'filepath: {filepath}')
                filestore.get(datafile, filepath)
        try:
            os.remove(f'{filepath}.lock')
        except OSError:
            logging.info(f'Failed to remove {filepath}.lock')

    def log_task_entry(slug, request_id, analysis_id):
        if slug:
            logging.info('\n')
            logging.info(f'====== {slug} '.ljust(90, '='))
        notify_api_task_started(analysis_id, request_id, slug)

    def log_params(params, kwargs):
        exclude_keys = [
            'fm_aggregation_profile',
            'accounts_profile',
            'oed_hierarchy',
            'exposure_profile',
            'lookup_config',
        ]
        print_params = {k: params[k] for k in set(list(params.keys())) - set(exclude_keys)}
        if settings.get('worker', 'DEBUG_MODE', fallback=False):
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
        params.setdefault('exposure_fp', os.path.join(params['root_run_dir'], 'location.csv'))
        params.setdefault('user_data_dir', os.path.join(params['root_run_dir'], f'user-data'))
        params.setdefault('analysis_settings_json', os.path.join(params['root_run_dir'], 'analysis_settings.json'))

        # Generate keys files
        params.setdefault('keys_fp', os.path.join(params['root_run_dir'], 'keys.csv'))
        params.setdefault('keys_errors_fp', os.path.join(params['root_run_dir'], 'keys-errors.csv'))

        # Fetch keyword args
        loc_file = kwargs.get('loc_file')
        acc_file = kwargs.get('acc_file')
        info_file = kwargs.get('info_file')
        scope_file = kwargs.get('scope_file')
        settings_file = kwargs.get('analysis_settings_file')
        complex_data_files = kwargs.get('complex_data_files')

        # Prepare 'generate-oasis-files' input files
        if loc_file:
            maybe_fetch_file(loc_file, params['exposure_fp'])

        if acc_file:
            params['accounts_fp'] = os.path.join(params['root_run_dir'], 'account.csv')
            maybe_fetch_file(acc_file, params['accounts_fp'])

        if info_file:
            params['ri_info_fp'] = os.path.join(params['root_run_dir'], 'reinsinfo.csv')
            maybe_fetch_file(info_file, params['ri_info_fp'])

        if scope_file:
            params['ri_scope_fp'] = os.path.join(params['root_run_dir'], 'reinsscope.csv')
            maybe_fetch_file(scope_file, params['ri_scope_fp'])

        if settings_file:
            maybe_fetch_file(settings_file, params['analysis_settings_json'])

        if complex_data_files:
            maybe_prepare_complex_data_files(complex_data_files, params['user_data_dir'])

        log_params(params, kwargs)

    def run(self, params, *args, run_data_uuid=None, analysis_id=None, **kwargs):
        log_task_entry(kwargs.get('slug'), self.request.id, analysis_id)

        ## add check for work-lost function here
        # check_worker_lost(task, analysis_pk)
        #from celery.contrib import rdb
        #rdb.set_trace()


        if isinstance(params, list):
            for p in params:
                _prepare_directories(p, analysis_id, run_data_uuid, kwargs)
        else:
            _prepare_directories(params, analysis_id, run_data_uuid, kwargs)

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

    if config.get('lookup_config_json'):
        lookup_config_json = os.path.join(
            os.path.dirname(config_path),
            config.get('lookup_config_json'))
    else:
        lookup_config_json = None

    # Remove pos arg for 'target_dir' and 'location_file'
    params = OasisManager()._params_generate_files(
        oasis_files_dir=params['target_dir'],
        oed_location_csv=params['exposure_fp'],
        model_version_csv=config.get('model_version_csv', None),
        lookup_module_path=config.get('lookup_package_dir', None),
        lookup_config_json=lookup_config_json,
        disable_summarise_exposure=settings.getboolean('worker', 'DISABLE_EXPOSURE_SUMMARY', fallback=False),
        lookup_multiprocessing=multiprocessing,
    )
    # debug print
    #print(json.dumps(params, indent=4))

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
        #lookup_config = params['lookup_config_json']
        #print("LOOKUP CONFIG")
        #print(lookup_config)
        #if lookup_config and lookup_config['keys_data_path'] in ['.', './']:
        #    lookup_config['keys_data_path'] = os.path.join(os.path.dirname(params['lookup_config_fp']))
        #elif lookup_config and not os.path.isabs(lookup_config['keys_data_path']):
        #    lookup_config['keys_data_path'] = os.path.join(os.path.dirname(params['lookup_config_fp']), lookup_config['keys_data_path'])


        ## refactor this to call the manager class
        _, lookup = OasisLookupFactory.create(
            lookup_config_fp=params['lookup_config_json'],
            model_keys_data_path=params['lookup_data_dir'],
            model_version_file_path=params['model_version_csv'],
            lookup_module_path=params['lookup_module_path'],
            complex_lookup_config_fp=params['lookup_complex_config_json'],
            user_data_dir=params['user_data_dir'],
            output_directory=chunk_target_dir,
        )

        location_df = lookup.get_locations(location_fp=params['exposure_fp'],
        )

        location_df = pd.np.array_split(location_df, num_chunks)[chunk_idx]
        chunk_keys_fp = os.path.join(chunk_target_dir, 'keys.csv')
        chunk_keys_errors_fp = os.path.join(chunk_target_dir, 'keys-errors.csv')

        lookup.generate_key_files_singleproc(
            loc_df=location_df,
            successes_fp=chunk_keys_fp,
            errors_fp=chunk_keys_errors_fp,
            output_format='oasis',
            keys_success_msg=False,
        )

        # Store chunks
        storage_subdir = f'{run_data_uuid}/oasis-files'
        params['chunk_keys'] = filestore.put(
            chunk_keys_fp,
            filename=f'{chunk_idx}-keys-chunk.csv',
            subdir=params['storage_subdir']
        )
        params['chunk_keys_errors'] = filestore.put(
            chunk_keys_errors_fp,
            filename=f'{chunk_idx}-keys-error-chunk.csv',
            subdir=params['storage_subdir']
        )

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
    del chunk_params['chunk_keys_errors']

    chunk_keys = [d['chunk_keys'] for d in params]
    chunk_errors = [d['chunk_keys_errors'] for d in params]
    logging.info('chunk_keys: {}'.format(chunk_keys))
    logging.info('chunk_errors: {}'.format(chunk_errors))

    def load_dataframes(paths):
        for p in paths:
            try:
                df = pd.read_csv(p)
                yield df
            #except OasisException:
            except Exception:
                logging.info('Failed to load chunk: {}'.format(p))
                pass

    with TemporaryDir() as working_dir:
        # Collect Keys
        filelist_keys = [filestore.get(
            chunk_idx,
            working_dir,
            subdir=storage_subdir,
        ) for chunk_idx in chunk_keys]

        # Collect keys-errors
        filelist_errors = [filestore.get(
            chunk_idx,
            working_dir,
            subdir=storage_subdir,
        ) for chunk_idx in chunk_errors]

        logging.info('filelist_keys: {}'.format(filelist_keys))
        logging.info('filelist_errors: {}'.format(filelist_errors))

        keys_frames = list(load_dataframes(filelist_keys))
        if keys_frames:
            keys = pd.concat(keys_frames)
            keys_file = os.path.join(working_dir, 'keys.csv')
            keys.to_csv(keys_file, index=False, encoding='utf-8')

            chunk_params['keys_ref'] = filestore.put(
                keys_file,
                filename=f'keys.csv',
                subdir=storage_subdir
            )
        else:
            chunk_params['keys_ref'] = None

        errors_frames = list(load_dataframes(filelist_errors))
        if errors_frames:
            keys_errors = pd.concat(errors_frames)
            keys_errors_file = os.path.join(working_dir, 'keys-errors.csv')
            keys_errors.to_csv(keys_errors_file, index=False, encoding='utf-8')

            chunk_params['keys_error_ref'] = filestore.put(
                keys_errors_file,
                filename='keys-errors.csv',
                subdir=storage_subdir
            )
        else:
            chunk_params['keys_errors_ref'] = None

    return chunk_params


@app.task(bind=True, name='write_input_files', **celery_conf.worker_task_kwargs)
@keys_generation_task
def write_input_files(self, params, run_data_uuid=None, analysis_id=None, initiator_id=None, slug=None, **kwargs):
    params['keys_fp'] = filestore.get(params['keys_ref'], params['target_dir'], subdir=params['storage_subdir'])
    params['keys_errors_fp'] = filestore.get(params['keys_error_ref'], params['target_dir'], subdir=params['storage_subdir'])
    #params['fm_aggregation_profile'] = {int(k): v for k, v in params['fm_aggregation_profile'].items()}
    #OasisManager().prepare_input_generation_params(**params)
    #OasisManager().prepare_input_directory(**params)
    #OasisManager().write_input_files(**params)
    OasisManager().generate_files(**params)

    return {
        'lookup_error_location': filestore.put(os.path.join(params['target_dir'], 'keys-errors.csv')),
        'lookup_success_location': filestore.put(os.path.join(params['target_dir'], 'gul_summary_map.csv')),
        'lookup_validation_location': filestore.put(os.path.join(params['target_dir'], 'exposure_summary_report.json')),
        'summary_levels_location': filestore.put(os.path.join(params['target_dir'], 'exposure_summary_levels.json')),
        'output_location': filestore.put(params['target_dir']),
    }


@app.task(bind=True, name='cleanup_input_generation', **celery_conf.worker_task_kwargs)
@keys_generation_task
def cleanup_input_generation(self, params, analysis_id=None, initiator_id=None, run_data_uuid=None, slug=None):
    if not settings.getboolean('worker', 'KEEP_RUN_DIR', fallback=False):
        # Delete local copy of run data
        shutil.rmtree(params['target_dir'], ignore_errors=True)
    if not settings.getboolean('worker', 'KEEP_CHUNK_DATA', fallback=False):
        # Delete remote copy of run data
        filestore.delete_dir(params['storage_subdir'])

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
        print_params = {k: params[k] for k in set(list(params.keys())) - set(exclude_keys)}
        if settings.get('worker', 'DEBUG_MODE', fallback=True):
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
        log_params(params, kwargs)

    def run(self, params, *args, run_data_uuid=None, analysis_id=None, **kwargs):
        log_task_entry(kwargs.get('slug'), self.request.id, analysis_id)
        ## add check for work-lost function here
        # check_worker_lost(task, analysis_pk)

        if isinstance(params, list):
            for p in params:
                _prepare_directories(p, analysis_id, run_data_uuid, kwargs)
        else:
            _prepare_directories(params, analysis_id, run_data_uuid, kwargs)
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

    if config.get('model_data_dir'):
        model_data_dir = os.path.join(
            os.path.dirname(config_path),
            config.get('model_data_dir'))
    else:
        model_data_dir = None

    run_params = {**config, **params}
    run_params["model_data_dir"] = model_data_dir

    print(run_params)

    return OasisManager()._params_generate_losses(**run_params)


    #return OasisManager().prepare_loss_generation_params(
    #    model_data_fp=config.get('model_data_dir'),
    #    model_package_fp=config.get('model_package_dir'),
    #    model_custom_gulcalc=config.get('model_custom_gulcalc'),
    #    ktools_error_guard=settings.getboolean('worker', 'KTOOLS_ERROR_GUARD', fallback=True),
    #    ktools_debug=settings.getboolean('worker', 'DEBUG_MODE', fallback=False),
    #    ktools_fifo_queue_dir=os.path.join(params['model_run_dir'], 'fifo'),
    #    ktools_work_dir=os.path.join(params['model_run_dir'], 'work'),
    #    ktools_alloc_rule_gul=settings.get('worker', 'KTOOLS_ALLOC_RULE_GUL', fallback=None),
    #    ktools_alloc_rule_il=settings.get('worker', 'KTOOLS_ALLOC_RULE_IL', fallback=None),
    #    ktools_alloc_rule_ri=settings.get('worker', 'KTOOLS_ALLOC_RULE_RI', fallback=None),
    #    ktools_num_processes=num_chunks,
    #    **params,
    #)


@app.task(bind=True, name='prepare_losses_generation_directory', **celery_conf.worker_task_kwargs)
@loss_generation_task
def prepare_losses_generation_directory(self, params, analysis_id=None, slug=None, **kwargs):
    params['analysis_settings'] = OasisManager().generate_losses_dir(**params)
    params['run_location'] = filestore.put(
        params['model_run_dir'],
        filename='run_directory.tar.gz',
        subdir=params['storage_subdir']
    )
    return params


@app.task(bind=True, name='generate_losses_chunk', **celery_conf.worker_task_kwargs)
@loss_generation_task
def generate_losses_chunk(self, params, chunk_idx, num_chunks, analysis_id=None, slug=None, **kwargs):

    print(params)

    chunk_params = {
        **params,
        'process_number': chunk_idx+1,
        'max_process_id' : num_chunks,
        'ktools_fifo_relative': True,
        'ktools_work_dir': os.path.join(params['model_run_dir'], 'work'),
    }
    Path(chunk_params['ktools_work_dir']).mkdir(parents=True, exist_ok=True)
    OasisManager().generate_losses_partial(**chunk_params)

    return {
        **params,
        'chunk_work_location': filestore.put(
            chunk_params['ktools_work_dir'],
            filename=f'work-{chunk_idx}.tar.gz',
            subdir=params['storage_subdir']
        ),
        #'chunk_script_path': chunk_params['script_fp'],
        #'ktools_fifo_queue_dir': chunk_params['ktools_fifo_queue_dir'],
        'ktools_work_dir': chunk_params['ktools_work_dir'],
        'process_number': chunk_idx + 1,
    }


@app.task(bind=True, name='generate_losses_output', **celery_conf.worker_task_kwargs)
@loss_generation_task
def generate_losses_output(self, params, analysis_id=None, slug=None, **kwargs):
    res = {**params[0]}
    abs_work_dir = os.path.join(
        res['model_run_dir'],
        res['ktools_work_dir'],
    )
    Path(abs_work_dir).mkdir(exist_ok=True, parents=True)

    # collect the run results
    for p in params:
        with TemporaryDir() as d:
            filestore.extract(p['chunk_work_location'], d, p['storage_subdir'])
            merge_dirs(d, abs_work_dir)

    OasisManager().generate_losses_output(**res)

    # OASISLMF update - output the bash trace of each run to combine for logging
    #res['bash_trace'] = '\n\n'.join(
    #    f'Analysis Chunk {idx}:\n{chunk["bash_trace"]}' for idx, chunk in enumerate(params)
    #)
    res['bash_trace'] = ""

    return {
        **res,
        'output_location': filestore.put(os.path.join(res['model_run_dir'], 'output'), arcname='output'),
        'log_location': filestore.put(os.path.join(res['model_run_dir'], 'log')),
    }


@app.task(bind=True, name='cleanup_losses_generation', **celery_conf.worker_task_kwargs)
@loss_generation_task
def cleanup_losses_generation(self, params, analysis_id=None, slug=None, **kwargs):
    if not settings.getboolean('worker', 'KEEP_RUN_DIR', fallback=False):
        # Delete local copy of run data
        shutil.rmtree(params['root_run_dir'], ignore_errors=True)
    if not settings.getboolean('worker', 'KEEP_CHUNK_DATA', fallback=False):
        # Delete remote copy of run data
        filestore.delete_dir(params['storage_subdir'])

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
