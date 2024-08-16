from __future__ import absolute_import

import glob
import json
import logging
import os
import pathlib
import tempfile
import shutil
from datetime import datetime

import filelock
import numpy as np
import pandas as pd
import numpy as np
from celery import Celery, signature
from celery.utils.log import get_task_logger
from celery.signals import (task_failure, task_revoked, worker_ready)
from natsort import natsorted
from oasislmf.model_preparation.lookup import OasisLookupFactory
from oasislmf.utils.data import get_json
from oasislmf.utils.status import OASIS_TASK_STATUS
from pathlib2 import Path

from ..common.filestore.filestore import get_filestore
from ..conf import celeryconf_v2 as celery_conf
from ..conf.iniconf import settings, settings_local
from .celery_request_handler import WorkerLostRetry
from .utils import (
    LoggingTaskContext,
    log_params,
    paths_to_absolute_paths,
    TemporaryDir,
    get_oasislmf_config_path,
    get_model_settings,
    get_worker_versions,
    merge_dirs,
    prepare_complex_model_file_inputs,
    config_strip_default_exposure,
)


'''
Celery task wrapper for Oasis ktools calculation.
'''

logger = get_task_logger(__name__)
LOG_FILE_SUFFIX = 'txt'
ARCHIVE_FILE_SUFFIX = 'tar.gz'
RUNNING_TASK_STATUS = OASIS_TASK_STATUS["running"]["id"]
TASK_LOG_DIR = settings.get('worker', 'TASK_LOG_DIR', fallback='/var/log/oasis/tasks')
FAIL_ON_REDELIVERY = settings.getboolean('worker', 'FAIL_ON_REDELIVERY', fallback=True)


app = Celery(task_cls=WorkerLostRetry)
app.config_from_object(celery_conf)
filestore = get_filestore(settings)
model_storage = get_filestore(settings_local, "worker.model_data", raise_error=False)
# print(app._conf)


logger.info("Started worker")
debug_worker = settings.getboolean('worker', 'DEBUG', fallback=False)

# Quiet sub-loggers
logging.getLogger('billiard').setLevel('INFO')
logging.getLogger('numba').setLevel('INFO')


def notify_api_status(analysis_pk, task_status):
    logger.info("Notify API: analysis_id={}, status={}".format(
        analysis_pk,
        task_status
    ))
    signature(
        'set_task_status_v2',
        args=(analysis_pk, task_status, datetime.now().timestamp()),
        queue='celery-v2'
    ).delay()


def notify_subtask_status(analysis_id, initiator_id, task_slug, subtask_status, error_msg=''):
    logger.info(f"Notify API: analysis_id={analysis_id}, task_slug={task_slug}  status={subtask_status}, error={error_msg}")
    signature(
        'set_subtask_status',
        args=(analysis_id, initiator_id, task_slug, subtask_status, error_msg),
        queue='celery-v2'
    ).delay()


def load_location_data(loc_filepath, oed_schema_info=None):
    """ Returns location file as DataFrame

    Returns a DataFrame of Loaction data with 'loc_id' row assgined
    has a fallback to support both 1.26 and 1.27 versions of oasislmf
    """
    try:
        # oasislmf == 1.26.x or 1.23.x
        from oasislmf.utils.data import get_location_df
        return get_location_df(loc_filepath)
    except ImportError:
        # oasislmf == 1.27.x or greater
        from oasislmf.utils.data import prepare_location_df
        from ods_tools.oed.exposure import OedExposure

        exposure = OedExposure(
            location=pathlib.Path(os.path.abspath(loc_filepath)),
            oed_schema_info=oed_schema_info,
        )
        exposure.location.dataframe = prepare_location_df(exposure.location.dataframe)
        return exposure.location.dataframe


def check_task_redelivered(task, analysis_id, initiator_id, task_slug, error_state):
    """ Safe guard to check if task has been attempted on worker
    and was redelivered.

    If 'OASIS_FAIL_ON_REDELIVERED=True' attempt the task 3 times
    then give up and mark it as failed. This is to prevent a worker
    crashing with OOM repeatedly failing on the same sub-task
    """
    if FAIL_ON_REDELIVERY:
        redelivered = task.request.delivery_info.get('redelivered')
        state = task.AsyncResult(task.request.id).state
        logger.debug('--- check_task_redelivered ---')
        logger.debug(f'task: {task_slug}')
        logger.debug(f"redelivered: {redelivered}")
        logger.debug(f"state: {state}")

        if state == 'REVOKED':
            logger.error('ERROR: task requeued three times or cancelled - aborting task')
            notify_subtask_status(
                analysis_id=analysis_id,
                initiator_id=initiator_id,
                task_slug=task_slug,
                subtask_status='ERROR',
                error_msg='Task revoked, possible out of memory error or cancellation'
            )
            notify_api_status(analysis_id, error_state)
            task.app.control.revoke(task.request.id, terminate=True)
            return
        if state == 'RETRY':
            logger.info('WARNING: task requeue detected - retry 2')
            task.update_state(state='REVOKED')
            return
        if redelivered:
            logger.info('WARNING: task requeue detected - retry 1')
            task.update_state(state='RETRY')
            return

# https://docs.celeryproject.org/en/latest/userguide/signals.html#task-revoked


@task_revoked.connect
def revoked_handler(*args, **kwargs):
    request = kwargs.get('request')
    analysis_id = request.kwargs.get('analysis_id', None)
    task_controller_queue = settings.get('worker', 'TASK_CONTROLLER_QUEUE', fallback='celery-v2')

    if analysis_id:
        signature('cancel_subtasks', args=[analysis_id], queue=task_controller_queue).delay()
    else:
        app.control.revoke(request.id, terminate=True)
    if request.chain:
        request.chain[:] = []

# When a worker connects send a task to the worker-monitor to register a new model


@worker_ready.connect
def register_worker(sender, **k):

    m_supplier = os.environ.get('OASIS_MODEL_SUPPLIER_ID')
    m_name = os.environ.get('OASIS_MODEL_ID')
    m_id = os.environ.get('OASIS_MODEL_VERSION_ID')
    m_settings = get_model_settings(settings)
    m_version = get_worker_versions()
    m_conf = get_json(get_oasislmf_config_path(settings, m_id))
    logger.info('register_worker: SUPPLIER_ID={}, MODEL_ID={}, VERSION_ID={}'.format(m_supplier, m_name, m_id))
    logger.info('versions: {}'.format(m_version))
    logger.info('settings: {}'.format(m_settings))
    logger.info('oasislmf config: {}'.format(m_conf))

    # Check for 'DISABLE_WORKER_REG' before se:NERDTreeToggle
    # unding task to API
    if settings.getboolean('worker', 'DISABLE_WORKER_REG', fallback=False):
        logger.info(('Worker auto-registration DISABLED: to enable:\n'
                     '  set DISABLE_WORKER_REG=False in conf.ini or\n'
                     '  set the envoritment variable OASIS_DISABLE_WORKER_REG=False'))
    else:
        logger.info('Auto registrating with the Oasis API:')
        m_settings = get_model_settings(settings)
        logger.info('settings: {}'.format(m_settings))

        signature(
            'run_register_worker_v2',
            args=(m_supplier, m_name, m_id, m_settings, m_version, m_conf),
            queue='celery-v2',
        ).delay()

    # Required ENV
    logger.info("LOCK_FILE: {}".format(settings.get('worker', 'LOCK_FILE')))
    logger.info("LOCK_TIMEOUT_IN_SECS: {}".format(settings.getfloat('worker', 'LOCK_TIMEOUT_IN_SECS')))
    logger.info("LOCK_RETRY_COUNTDOWN_IN_SECS: {}".format(settings.get('worker', 'LOCK_RETRY_COUNTDOWN_IN_SECS')))

    # Storage Mode
    selected_storage = settings.get('worker', 'STORAGE_TYPE', fallback="").lower()
    logger.info("STORAGE_MANAGER: {}".format(type(filestore)))
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
    logger.info("KEEP_LOCAL_DATA: {}".format(settings.get('worker', 'KEEP_LOCAL_DATA', fallback='False')))
    logger.info("KEEP_REMOTE_DATA: {}".format(settings.get('worker', 'KEEP_REMOTE_DATA', fallback='False')))
    logger.info("BASE_RUN_DIR: {}".format(settings.get('worker', 'BASE_RUN_DIR', fallback='None')))
    logger.info("OASISLMF_CONFIG: {}".format(settings.get('worker', 'oasislmf_config', fallback='None')))
    logger.info("TASK_LOG_DIR: {}".format(settings.get('worker', 'TASK_LOG_DIR', fallback='/var/log/oasis/tasks')))
    logger.info("FAIL_ON_REDELIVERY: {}".format(settings.getboolean('worker', 'FAIL_ON_REDELIVERY', fallback='True')))

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


# Send notification back to the API Once task is read from Queue
def notify_api_task_started(analysis_id, task_id, task_slug):
    logger.info("Notify API tasks has started: analysis_id={}, task_id={}, task_slug={}".format(
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
        logger.debug('Task chain header is already sorted')
    chain_tasks = task_request.chain[0]
    task_update_list = list()

    # Sequential tasks - in the celery task chain, important for stopping stalls on a cancellation request
    seq = {t['options']['task_id']: t['kwargs'] for t in chain_tasks['kwargs']['body']['kwargs']['tasks']}
    for task_id in seq:
        task_update_list.append((task_id, seq[task_id]['analysis_id'], seq[task_id]['slug']))

    # Chunked tasks - This call might get heavy as the chunk load increases (possibly remove later)
    chunks = {t['options']['task_id']: t['kwargs'] for t in chain_tasks['kwargs']['header']['kwargs']['tasks']}
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
                    prepare_complex_model_file_inputs(complex_data_files, str(user_data_path), filestore)
        try:
            os.remove('{user_data_dir}.lock')
        except OSError:
            logger.info(f'Failed to remove {user_data_dir}.lock')

    def maybe_fetch_file(datafile, filepath, subdir=''):
        with filelock.FileLock(f'{filepath}.lock'):
            if not Path(filepath).exists():
                logger.info(f'file: {datafile}')
                logger.info(f'filepath: {filepath}')
                filestore.get(datafile, filepath, subdir)
        try:
            os.remove(f'{filepath}.lock')
        except OSError:
            logger.info(f'Failed to remove {filepath}.lock')

    def get_file_ref(kwargs, params, arg_name):
        """ Either fetch file ref from Kwargs or override from pre-analysis hook
        """
        file_from_server = kwargs.get(arg_name)
        file_from_hook = params.get(f'pre_{arg_name}')
        if not file_from_server:
            logger.info(f'{arg_name}: (Not loaded)')
            return None
        elif file_from_hook:
            logger.info(f'{arg_name}: {file_from_hook} (pre-analysis-hook)')
            return file_from_hook
        logger.info(f'{arg_name}: {file_from_server} (portfolio)')
        return file_from_server

    def log_task_entry(slug, request_id, analysis_id):
        if slug:
            logger.info('\n')
            logger.info(f'====== {slug} '.ljust(90, '='))
        notify_api_task_started(analysis_id, request_id, slug)

    def log_task_params(params, kwargs):
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
        if debug_worker:
            log_params(params, kwargs, exclude_keys)

    def _prepare_directories(params, analysis_id, run_data_uuid, kwargs):
        params['storage_subdir'] = f'analysis-{analysis_id}_files-{run_data_uuid}'
        params['root_run_dir'] = os.path.join(settings.get('worker', 'base_run_dir', fallback='/tmp/run'), params['storage_subdir'])
        Path(params['root_run_dir']).mkdir(parents=True, exist_ok=True)

        # Set `oasis-file-generation` input files
        params.setdefault('target_dir', params['root_run_dir'])
        params.setdefault('user_data_dir', os.path.join(params['root_run_dir'], 'user-data'))
        params.setdefault('lookup_complex_config_json', os.path.join(params['root_run_dir'], 'analysis_settings.json'))
        params.setdefault('analysis_settings_json', os.path.join(params['root_run_dir'], 'analysis_settings.json'))

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
            params['oed_location_csv'] = os.path.join(params['root_run_dir'], f'location{loc_extention}')
            maybe_fetch_file(loc_file, params['oed_location_csv'])
        if acc_file:
            acc_extention = "".join(pathlib.Path(acc_file).suffixes)
            params['oed_accounts_csv'] = os.path.join(params['root_run_dir'], f'account{acc_extention}')
            maybe_fetch_file(acc_file, params['oed_accounts_csv'])
        if info_file:
            info_extention = "".join(pathlib.Path(info_file).suffixes)
            params['oed_info_csv'] = os.path.join(params['root_run_dir'], f'reinsinfo{info_extention}')
            maybe_fetch_file(info_file, params['oed_info_csv'])
        if scope_file:
            scope_extention = "".join(pathlib.Path(scope_file).suffixes)
            params['oed_scope_csv'] = os.path.join(params['root_run_dir'], f'reinsscope{scope_extention}')
            maybe_fetch_file(scope_file, params['oed_scope_csv'])

        # Complex model lookup files
        if settings_file:
            maybe_fetch_file(settings_file, params['lookup_complex_config_json'])
        else:
            params['lookup_complex_config_json'] = None
            params['analysis_settings_json'] = None
        if complex_data_files:
            maybe_prepare_complex_data_files(complex_data_files, params['user_data_dir'])
        else:
            params['user_data_dir'] = None

    def run(self, params, *args, run_data_uuid=None, analysis_id=None, **kwargs):
        kwargs['log_filename'] = os.path.join(TASK_LOG_DIR, f"{run_data_uuid}_{kwargs.get('slug')}.log")
        # log_level = 'DEBUG' if debug_worker else 'INFO'
        log_level = 'INFO'
        with LoggingTaskContext(logging.getLogger(), log_filename=kwargs['log_filename'], level=log_level):
            log_task_entry(kwargs.get('slug'), self.request.id, analysis_id)

            if isinstance(params, list):
                for p in params:
                    _prepare_directories(p, analysis_id, run_data_uuid, kwargs)
            else:
                _prepare_directories(params, analysis_id, run_data_uuid, kwargs)

            log_task_params(params, kwargs)
            check_task_redelivered(self,
                                   analysis_id=analysis_id,
                                   initiator_id=kwargs.get('initiator_id'),
                                   task_slug=kwargs.get('slug'),
                                   error_state='INPUTS_GENERATION_ERROR'
                                   )
            try:
                return fn(self, params, *args, analysis_id=analysis_id, run_data_uuid=run_data_uuid, **kwargs)
            except Exception as error:
                # fallback only needed if celery can't serialize the exception
                logger.exception("Error occured in 'keys_generation_task':")
                raise error

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
    update_all_tasks_ids(self.request)  # updates all the assigned task_ids

    model_id = settings.get('worker', 'model_id')
    config_path = get_oasislmf_config_path(settings, model_id)
    config = config_strip_default_exposure(get_json(config_path))
    lookup_params = {**config, **params}

    from oasislmf.manager import OasisManager
    gen_files_params = OasisManager()._params_generate_oasis_files(**lookup_params)
    params = paths_to_absolute_paths({**gen_files_params}, config_path)

    params['log_storage'] = dict()
    params['log_location'] = filestore.put(kwargs.get('log_filename'))
    params['log_storage'][slug] = params['log_location']
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
            from oasislmf.manager import OasisManager
            pre_hook_output = OasisManager().exposure_pre_analysis(**params)
            files_modified = pre_hook_output.get('modified', {})

            # store updated files
            pre_loc_fp = os.path.join(hook_target_dir, files_modified.get('location'))
            params['pre_loc_file'] = filestore.put(
                pre_loc_fp,
                filename=os.path.basename(pre_loc_fp),
                subdir=params['storage_subdir']
            )
            if files_modified.get('account'):
                pre_acc_fp = os.path.join(hook_target_dir, files_modified.get('account'))
                params['pre_acc_file'] = filestore.put(
                    pre_acc_fp,
                    filename=os.path.basename(pre_acc_fp),
                    subdir=params['storage_subdir']
                )
            if files_modified.get('ri_info'):
                pre_info_fp = os.path.join(hook_target_dir, files_modified.get('ri_info'))
                params['pre_info_file'] = filestore.put(
                    pre_info_fp,
                    filename=os.path.basename(pre_info_fp),
                    subdir=params['storage_subdir']
                )
            if files_modified.get('ri_scope'):
                pre_scope_fp = os.path.join(hook_target_dir, files_modified.get('ri_scope'))
                params['pre_scope_file'] = filestore.put(
                    pre_scope_fp,
                    filename=os.path.basename(pre_scope_fp),
                    subdir=params['storage_subdir']
                )

            # OED has been loaded and check in this step, disable check in file gen
            # This is in case pre-exposure func has added non-standard cols to the file.
            params['check_oed'] = False
    else:
        logger.info('pre_generation_hook: SKIPPING, param "exposure_pre_analysis_module" not set')
    params['log_location'] = filestore.put(kwargs.get('log_filename'))
    params['log_storage'][slug] = params['log_location']
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

        _, lookup = OasisLookupFactory.create(
            lookup_config_fp=params.get('lookup_config_json', None),
            model_keys_data_path=params.get('lookup_data_dir', None),
            model_version_file_path=params.get('model_version_csv', None),
            lookup_module_path=params.get('lookup_module_path', None),
            complex_lookup_config_fp=params.get('lookup_complex_config_json', None),
            user_data_dir=params.get('user_data_dir', None),
            output_directory=chunk_target_dir,
        )

        location_df = load_location_data(
            loc_filepath=params['oed_location_csv'],
            oed_schema_info=params.get('oed_schema_info', None)
        )
        location_df = np.array_split(location_df, num_chunks)[chunk_idx]
        location_df.reset_index(drop=True, inplace=True)

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
        params['chunk_keys'] = filestore.put(
            chunk_target_dir,
            filename=f'lookup-{chunk_idx+1}.tar.gz',
            subdir=params['storage_subdir']
        )

    params['log_location'] = filestore.put(kwargs.get('log_filename'))
    params['log_storage'][slug] = params['log_location']
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

    def merge_dataframes(paths, output_file, file_type):
        pd_read_func = getattr(pd, f"read_{file_type}")
        if not paths:
            logger.warning("merge_dataframes was called with an empty path list.")
            return
        df_chunks = []
        for path in paths:
            try:
                df_chunks.append(pd_read_func(path))
            except pd.errors.EmptyDataError:
                # Ignore empty files.
                logger.info(f"File {path} is empty. --skipped--")

        if not df_chunks:
            logger.warning(f"All files were empty: {paths}. --skipped--")
            return
        # add opt for Select merge strat
        df = pd.concat(df_chunks)

        if file_type == 'parquet':
            # Parquet files should have an index which can be used to filter duplicates.
            df = df[~df.index.duplicated(keep='first')]
        elif file_type == 'csv':
            # CSV files only have an automatic index so we use the values themselves to filter dups.
            df = df[~df.duplicated(keep='first')]
        pd_write_func = getattr(df, f"to_{file_type}")
        # Only write index for parquet files to avoid useless extra column for csv files.
        pd_write_func(output_file, index=file_type == 'parquet')

    def take_first(paths, output_file):
        first_path = paths[0]
        logger.info(f"Using {first_path} and ignoring others.")
        shutil.copy2(first_path, output_file)

    # Collect files and tar here from chunk_params['target_dir']
    with TemporaryDir() as chunks_dir:
        chunks_dir = Path(chunks_dir)
        # extract chunks
        chunk_tars = [Path(d['chunk_keys']) for d in params]
        for tar in chunk_tars:
            dirname = tar.name.rstrip(''.join(tar.suffixes))
            extract_to = chunks_dir / dirname
            filestore.extract(tar.as_posix(), extract_to.as_posix(), storage_subdir)

        file_paths = list(chunks_dir.glob('lookup-[0-9]*/*'))  # all files that need merging (merge inputs)
        file_names = {path.name for path in file_paths}  # unique filenames (merge outputs)

        with TemporaryDir() as merge_dir:
            for file in file_names:
                logger.info(f'Merging into file: "{file}"')
                merge_dir = Path(merge_dir)
                file_type = Path(file).suffix[1:]
                file_name = Path(file).stem
                file_chunks = [f for f in file_paths if f.name == file]
                file_merged = merge_dir / file
                file_chunks = natsorted(file_chunks)

                if file_name in ['events', 'occurrence', 'ensemble_mapping']:
                    take_first(file_chunks, file_merged)
                elif file_type in ['csv', 'parquet']:
                    merge_dataframes(file_chunks, file_merged, file_type)
                else:
                    logger.info(f'No merge method for file: "{file}" --skipped--')

            # store keys data
            chunk_params['keys_data'] = filestore.put(
                merge_dir.as_posix(),
                filename='keys-data.tar.gz',
                subdir=chunk_params['storage_subdir']
            )

    chunk_params['log_location'] = filestore.put(kwargs.get('log_filename'))
    chunk_params['log_storage'][slug] = chunk_params['log_location']
    return chunk_params


@app.task(bind=True, name='write_input_files', **celery_conf.worker_task_kwargs)
@keys_generation_task
def write_input_files(self, params, run_data_uuid=None, analysis_id=None, initiator_id=None, slug=None, **kwargs):
    # Load Collected keys data
    filestore.extract(params['keys_data'], params['target_dir'], params['storage_subdir'])
    params['keys_data_csv'] = os.path.join(params['target_dir'], 'keys.csv')
    params['keys_errors_csv'] = os.path.join(params['target_dir'], 'keys-errors.csv')
    params['oasis_files_dir'] = params['target_dir']
    from oasislmf.manager import OasisManager
    OasisManager().generate_files(**params)

    # Optional step (Post file generation Hook)
    if params.get('post_file_gen_module', None):
        logger.info(f"post_generation_hook: running {params.get('post_file_gen_module')}")
        OasisManager().post_file_gen(**params)

    # clear out user-data,
    # these files should not be sorted in the generated inputs tar
    if params['user_data_dir'] is not None:
        shutil.rmtree(params['user_data_dir'], ignore_errors=True)

    # collect logs here before archive is created
    params['log_location'] = filestore.put(kwargs.get('log_filename'))
    params['log_storage'][slug] = params['log_location']
    for log_ref in params['log_storage']:
        filestore.get(params['log_storage'][log_ref], os.path.join(params['target_dir'], 'log', f'v2-{log_ref}.txt'))

    return {
        'lookup_error_location': filestore.put(os.path.join(params['target_dir'], 'keys-errors.csv')),
        'lookup_success_location': filestore.put(os.path.join(params['target_dir'], 'gul_summary_map.csv')),
        'lookup_validation_location': filestore.put(os.path.join(params['target_dir'], 'exposure_summary_report.json')),
        'summary_levels_location': filestore.put(os.path.join(params['target_dir'], 'exposure_summary_levels.json')),
        'output_location': filestore.put(params['target_dir']),
        'log_location': params['log_location'],
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
    return {'input-location_generate-and-run': params.get('output_location')}


# --- loss generation tasks ------------------------------------------------ #


def loss_generation_task(fn):
    def maybe_extract_tar(filestore_ref, dst, storage_subdir=''):
        logger.info(f'filestore_ref: {filestore_ref}')
        logger.info(f'dst: {dst}')
        with filelock.FileLock(f'{dst}.lock'):
            if not Path(dst).exists():
                filestore.extract(filestore_ref, dst, storage_subdir)

    def maybe_prepare_complex_data_files(complex_data_files, user_data_dir):
        with filelock.FileLock(f'{user_data_dir}.lock'):
            if complex_data_files:
                user_data_path = Path(user_data_dir)
                if not user_data_path.exists():
                    user_data_path.mkdir(parents=True, exist_ok=True)
                    prepare_complex_model_file_inputs(complex_data_files, str(user_data_path), filestore)
        try:
            os.remove(f'{user_data_dir}.lock')
        except OSError:
            logger.info(f'Failed to remove {user_data_dir}.lock')

    def maybe_fetch_analysis_settings(analysis_settings_file, analysis_settings_fp):
        with filelock.FileLock(f'{analysis_settings_fp}.lock'):
            if not Path(analysis_settings_fp).exists():
                logger.info(f'analysis_settings_file: {analysis_settings_file}')
                logger.info(f'analysis_settings_fp: {analysis_settings_fp}')
                filestore.get(analysis_settings_file, analysis_settings_fp)
        try:
            os.remove(f'{analysis_settings_fp}.lock')
        except OSError:
            logger.info(f'Failed to remove {analysis_settings_fp}.lock')

    def log_task_entry(slug, request_id, analysis_id):
        if slug:
            logger.info('\n')
            logger.info(f'====== {slug} '.ljust(90, '='))
        notify_api_task_started(analysis_id, request_id, slug)

    def log_task_params(params, kwargs):
        if isinstance(params, list):
            params = params[0]
        if debug_worker:
            log_params(params, kwargs)

    def _prepare_directories(params, analysis_id, run_data_uuid, kwargs):
        print(json.dumps(params, indent=4))

        params['storage_subdir'] = f'analysis-{analysis_id}_losses-{run_data_uuid}'
        params['root_run_dir'] = os.path.join(settings.get('worker', 'base_run_dir', fallback='/tmp/run'), params['storage_subdir'])
        Path(params['root_run_dir']).mkdir(parents=True, exist_ok=True)

        params.setdefault('oasis_files_dir', os.path.join(params['root_run_dir'], 'input-data'))
        params.setdefault('model_run_dir', os.path.join(params['root_run_dir'], 'run-data'))
        params.setdefault('results_path', os.path.join(params['root_run_dir'], 'results-data'))
        params.setdefault('user_data_dir', os.path.join(params['root_run_dir'], 'user-data'))
        params.setdefault('analysis_settings_json', os.path.join(params['root_run_dir'], 'analysis_settings.json'))

        # case for 'generate_and_run'
        if params.get('input-location_generate-and-run'):
            kwargs['input_location'] = params.get('input-location_generate-and-run')
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
        # log_level = 'DEBUG' if debug_worker else 'INFO'
        log_level = 'INFO'
        with LoggingTaskContext(logging.getLogger(), log_filename=kwargs['log_filename'], level=log_level):
            log_task_entry(kwargs.get('slug'), self.request.id, analysis_id)
            if isinstance(params, list):
                for p in params:
                    _prepare_directories(p, analysis_id, run_data_uuid, kwargs)
            else:
                _prepare_directories(params, analysis_id, run_data_uuid, kwargs)

            log_task_params(params, kwargs)
            check_task_redelivered(self,
                                   analysis_id=analysis_id,
                                   initiator_id=kwargs.get('initiator_id'),
                                   task_slug=kwargs.get('slug'),
                                   error_state='RUN_ERROR'
                                   )
            try:
                return fn(self, params, *args, analysis_id=analysis_id, **kwargs)
            except Exception as error:
                # fallback only needed if celery can't serialize the exception
                logger.exception("Error occured in 'loss_generation_task':")
                raise error

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
    update_all_tasks_ids(self.request)  # updates all the assigned task_ids

    model_id = settings.get('worker', 'model_id')
    config_path = get_oasislmf_config_path(settings, model_id)
    config = config_strip_default_exposure(get_json(config_path))
    run_params = {**config, **params}

    from oasislmf.manager import OasisManager
    gen_losses_params = OasisManager()._params_generate_oasis_losses(**run_params)
    params = paths_to_absolute_paths({**gen_losses_params}, config_path)

    params['log_location'] = filestore.put(kwargs.get('log_filename'))
    params['verbose'] = debug_worker

    # needed incase input_data is missing on another node
    input_tar_generate_and_run = run_params.get('input-location_generate-and-run')
    if input_tar_generate_and_run:
        params['input-location_generate-and-run'] = input_tar_generate_and_run

    return params


@app.task(bind=True, name='prepare_losses_generation_directory', **celery_conf.worker_task_kwargs)
@loss_generation_task
def prepare_losses_generation_directory(self, params, analysis_id=None, slug=None, **kwargs):
    with tempfile.NamedTemporaryFile(mode="w+") as f:
        # build the config for the file store storage
        if model_storage:
            config = model_storage.to_config()
            json.dump(config, f)
            f.flush()
        params['model_storage_json'] = f.name if model_storage else None

        from oasislmf.manager import OasisManager
        params['analysis_settings'] = OasisManager().generate_losses_dir(**params)

        # Optional step (Pre losses hook) --- Before or after 'generate_losses_dir' ??
        if params.get('pre_loss_module', None):
            logger.info(f"pre_losses_hook: running {params.get('pre_loss_module')}")
            OasisManager().pre_loss(**params)

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
        max_chunk_id = params.get('ktools_num_processes', -1)
        work_dir = 'work'
    else:
        # Run a single ktools pipe
        current_chunk_id = chunk_idx + 1
        max_chunk_id = num_chunks
        work_dir = f'{current_chunk_id}.work'

    chunk_params = {
        **params,
        'process_number': current_chunk_id,
        'max_process_id': max_chunk_id,
        'ktools_fifo_relative': True,
        'ktools_work_dir': os.path.join(params['model_run_dir'], work_dir),
        'df_engine': json.dumps({
            "path": settings.get(
                'worker',
                'default_reader_engine',
                fallback='oasis_data_manager.df_reader.reader.OasisPandasReader'
            ),
            "options": settings.get(
                'worker.default_reader_engine_options',
                None,
                fallback={}
            ),
        }),
        'ktools_log_dir': os.path.join(params['model_run_dir'], 'log'),
    }

    with tempfile.NamedTemporaryFile(mode="w+") as f:
        # build the config for the file store storage
        if model_storage:
            config = model_storage.to_config()
            json.dump(config, f)
            f.flush()

        chunk_params['model_storage_json'] = f.name if model_storage else None
        Path(chunk_params['ktools_work_dir']).mkdir(parents=True, exist_ok=True)
        from oasislmf.manager import OasisManager
        OasisManager().generate_losses_partial(**chunk_params)

        return {
            **params,
            'chunk_work_location': filestore.put(
                chunk_params['ktools_work_dir'],
                filename=f'work-{chunk_idx+1}.tar.gz',
                subdir=params['storage_subdir']
            ),
            'chunk_log_location': filestore.put(
                chunk_params['ktools_log_dir'],
                filename=f'log-{chunk_idx+1}.tar.gz',
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
    res['model_storage_json'] = None

    # collect run results
    abs_work_dir = os.path.join(res['model_run_dir'], 'work')
    Path(abs_work_dir).mkdir(exist_ok=True, parents=True)
    for p in params:
        with TemporaryDir() as d:
            filestore.extract(p['chunk_work_location'], d, p['storage_subdir'])
            merge_dirs(d, abs_work_dir)

    # Exec losses
    from oasislmf.manager import OasisManager
    OasisManager().generate_losses_output(**res)
    if res.get('post_analysis_module', None):
        logger.info(f"post_losses_hook: running {res.get('post_analysis_module')}")
        OasisManager().post_analysis(**res)

    # collect run logs
    abs_log_dir = os.path.join(res['model_run_dir'], 'log')
    Path(abs_log_dir).mkdir(exist_ok=True, parents=True)
    for p in params:
        with TemporaryDir() as d:
            filestore.extract(p['chunk_log_location'], d, p['storage_subdir'])
            merge_dirs(d, abs_log_dir)

    output_dir = os.path.join(res['model_run_dir'], 'output')
    logs_dir = os.path.join(res['model_run_dir'], 'log')
    raw_output_files = list(filter(lambda f: f.endswith('.csv') or f.endswith('.parquet'), os.listdir(output_dir)))

    return {
        **res,
        'output_location': filestore.put(output_dir, arcname='output'),
        'run_logs': filestore.put(logs_dir),
        'log_location': filestore.put(kwargs.get('log_filename')),
        'raw_output_locations': {
            r: filestore.put(os.path.join(output_dir, r), arcname=f'output_{r}')
            for r in raw_output_files
        }
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


@task_failure.connect
def handle_task_failure(*args, sender=None, task_id=None, **kwargs):
    logger.info("Task error handler")
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
        logger.info(f"deleting remote data, {dir_remote_data}")
        filestore.delete_dir(dir_remote_data)
