from __future__ import absolute_import

import glob
import json
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
from contextlib import contextmanager, suppress
from datetime import datetime

import fasteners
import filelock
import pandas as pd
from celery import Celery, signature
from celery.signals import worker_ready, before_task_publish
from celery.task import task
from oasislmf import __version__ as mdk_version
from oasislmf.manager import OasisManager
from oasislmf.model_preparation.lookup import OasisLookupFactory
from oasislmf.utils.data import get_json
from oasislmf.utils.exceptions import OasisException
from oasislmf.utils.log import oasis_log
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


# When a worker connects send a task to the worker-monitor to register a new model
@worker_ready.connect
def register_worker(sender, **k):
    m_supplier = os.environ.get('OASIS_MODEL_SUPPLIER_ID')
    m_name = os.environ.get('OASIS_MODEL_ID')
    m_id = os.environ.get('OASIS_MODEL_VERSION_ID')
    num_analysis_chunks = os.environ.get('OASIS_MODEL_NUM_ANALYSIS_CHUNKS')
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
        kwargs={'num_analysis_chunks': num_analysis_chunks},
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


#
# input generation tasks
#


@task(bind=True, name='prepare_input_generation_params')
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
    logging.info("prepare_input_generation_params: {}".format(str(locals())))
    notify_api_task_started(analysis_id, self.request.id, slug)
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
    params = OasisManager().prepare_input_generation_params(
        target_dir=f'{run_data_uuid}/oasis-files',
        exposure_fp='',
        lookup_config_fp=lookup_config_json,
        summarise_exposure=not settings.getboolean('worker', 'DISABLE_EXPOSURE_SUMMARY', fallback=False),
        multiprocessing=multiprocessing,
    )

    # Store file References for `prepare_keys_file_chunk`
    params['loc_file_ref'] = loc_file
    params['acc_file_ref'] = acc_file
    params['inf_file_ref'] = info_file
    params['scope_file_ref'] = scope_file
    params['settings_file_ref'] = settings_file
    params['complex_data_files'] = complex_data_files

    logging.info(params)
    return params


@task(bind=True, name='prepare_keys_file_chunk')
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
    notify_api_task_started(analysis_id, self.request.id, slug)
    tmp_base = settings.get('worker', 'BASE_RUN_DIR', fallback=None)
    run_data_subdir = f'analysis-{analysis_id}-{run_data_uuid}'

    with TemporaryDir(persist=False, basedir=tmp_base) as chunk_target_dir:
        lookup_config = params['lookup_config']
        if lookup_config and lookup_config['keys_data_path'] in ['.', './']:
            lookup_config['keys_data_path'] = os.path.join(os.path.dirname(params['lookup_config_fp']))
        elif lookup_config and not os.path.isabs(lookup_config['keys_data_path']):
            lookup_config['keys_data_path'] = os.path.join(os.path.dirname(params['lookup_config_fp']), lookup_config['keys_data_path'])

        # TODO: download & setup and download `user_data_dir`
        # 'user_data_dir' and 'complex_lookup_config_fp'

        _, lookup = OasisLookupFactory.create(
            lookup_config=lookup_config,
            model_keys_data_path=params['keys_data_fp'],
            model_version_file_path=params['model_version_fp'],
            lookup_package_path=params['lookup_package_fp'],
            complex_lookup_config_fp=params['complex_lookup_config_fp'],
            user_data_dir=params['user_data_dir'],
            output_directory=chunk_target_dir,
        )

        # Fetch location file for Storage (possibly from Cache)
        location_file = filestore.get(params['loc_file_ref'], cache_dir=run_data_subdir)


        location_df = OasisLookupFactory.get_exposure(
            lookup=lookup,
            source_exposure_fp=location_file,
        )

        location_df = pd.np.array_split(location_df, num_chunks)[chunk_idx]
        chunk_keys_fp = os.path.join(chunk_target_dir, 'keys.csv')
        chunk_keys_errors_fp = os.path.join(chunk_target_dir, 'keys-errors.csv')

        OasisLookupFactory.save_results(
            lookup,
            location_df=location_df,
            successes_fp=chunk_keys_fp,
            errors_fp=chunk_keys_errors_fp,
            multiprocessing=params['multiprocessing'],
        )

        # Store chunks
        storage_subdir = f'{run_data_uuid}/oasis-files'
        params['chunk_keys'] = filestore.put(
            chunk_keys_fp,
            filename=f'{chunk_idx}-keys-chunk.csv',
            cache_dir=run_data_subdir,
            subdir=run_data_subdir
        )
        params['chunk_keys_errors'] = filestore.put(
            chunk_keys_errors_fp,
            filename=f'{chunk_idx}-keys-error-chunk.csv',
            cache_dir=run_data_subdir,
            subdir=run_data_subdir
        )

    return params


@task(bind=True, name='collect_keys')
def collect_keys(
    self,
    chunk_params,
    run_data_uuid=None,
    analysis_id=None,
    initiator_id=None,
    slug=None,
    **kwargs
 ):
    notify_api_task_started(analysis_id, self.request.id, slug)
    run_data_subdir = f'analysis-{analysis_id}-{run_data_uuid}'

    # Setup return params
    params = {**chunk_params[0]}
    del params['chunk_keys']
    del params['chunk_keys_errors']

    chunk_keys = [d['chunk_keys'] for d in chunk_params]
    chunk_errors = [d['chunk_keys_errors'] for d in chunk_params]
    logging.info('chunk_keys: {}'.format(chunk_keys))
    logging.info('chunk_errors: {}'.format(chunk_errors))

    def load_dataframes(paths):
        for p in paths:
            try:
                #df = get_dataframe(p)
                df = pd.read_csv(p)
                yield df
            #except OasisException:
            except Exception:
                logging.info('Failed to load chunk: {}'.format(p))
                pass


    tmpdir_base = settings.get('worker', 'BASE_RUN_DIR', fallback=None)
    with TemporaryDir(persist=False, basedir=tmpdir_base) as working_dir:

        # Collect Keys
        filelist_keys = [filestore.get(
            chunk_idx,
            working_dir,
            subdir=run_data_subdir,
            cache_dir=run_data_uuid
        ) for chunk_idx in chunk_keys]

        # Collect keys-errors
        filelist_errors = [filestore.get(
            chunk_idx,
            working_dir,
            subdir=run_data_subdir,
            cache_dir=run_data_uuid
        ) for chunk_idx in chunk_errors]

        logging.info('filelist_keys: {}'.format(filelist_keys))
        logging.info('filelist_errors: {}'.format(filelist_errors))

        keys_frames = list(load_dataframes(filelist_keys))
        if keys_frames:
            keys = pd.concat(keys_frames)
            keys_file = os.path.join(working_dir, 'keys.csv')
            keys.to_csv(keys_file, index=False, encoding='utf-8')

            params['keys_ref'] = filestore.put(
                keys_file,
                filename=f'keys.csv',
                cache_dir=run_data_subdir,
                subdir=run_data_subdir
            )
        else:
            params['keys_ref'] = None

        errors_frames = list(load_dataframes(filelist_errors))
        if errors_frames:
            keys_errors = pd.concat(errors_frames)
            keys_errors_file = os.path.join(working_dir, 'keys-errors.csv')
            keys_errors.to_csv(keys_errors_file, index=False, encoding='utf-8')

            params['keys_error_ref'] = filestore.put(
                keys_errors_file,
                filename='keys-errors.csv',
                cache_dir=run_data_subdir,
                subdir=run_data_subdir
            )
        else:
            params['keys_error_ref'] = None

        # Remove all keys-chunks for storage
        #f for f in chunk_keys + chunk_errors:
        #    filestore.delete(f ... )


    return params


@task(bind=True, name='write_input_files')
def write_input_files(self, params, run_data_uuid=None, analysis_id=None, initiator_id=None, slug=None, **kwargs):
    logging.info('write_input_files: analysis_id={}, initiator_id={}, slug={}'.format(
        analysis_id, initiator_id, slug
    ))

    # Stage load chunk references to filepaths
    run_data_subdir = f'analysis-{analysis_id}-{run_data_uuid}'
    tmp_persist = settings.getboolean('worker', 'KEEP_RUN_DIR', fallback=False)
    tmp_base = settings.get('worker', 'BASE_RUN_DIR', fallback=None)
    with TemporaryDir(persist=tmp_persist, basedir=tmp_base) as oasis_files_dir:

        #if complex_data_files:
        #    input_data_dir = os.path.join(run_dir_base, f'input-generation-input-data-dir-{analysis_id}-{uuid.uuid4().hex}')
        #    Path(input_data_dir).mkdir(parents=True, exist_ok=True)
        #else:
        #    params['user_data_dir']  = None

        params['target_dir']     = oasis_files_dir
        params['user_data_dir']  = None
        params['exposure_fp']    = filestore.get(params['loc_file_ref'],   oasis_files_dir, cache_dir=run_data_subdir)
        params['accounts_fp']    = filestore.get(params['acc_file_ref'],   oasis_files_dir, cache_dir=run_data_subdir)
        params['ri_scope_fp']    = filestore.get(params['scope_file_ref'], oasis_files_dir, cache_dir=run_data_subdir)
        params['ri_info_fp']     = filestore.get(params['inf_file_ref'],   oasis_files_dir, cache_dir=run_data_subdir)
        params['keys_fp']        = filestore.get(params['keys_ref'],       oasis_files_dir, subdir=run_data_subdir, cache_dir=run_data_subdir)
        params['keys_errors_fp'] = filestore.get(params['keys_error_ref'], oasis_files_dir, subdir=run_data_subdir, cache_dir=run_data_subdir)

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

        OasisManager().prepare_input_directory(**params)
        OasisManager().write_input_files(**params)

        output_params = {
            'lookup_error_location': filestore.put(os.path.join(oasis_files_dir, 'keys-errors.csv')),
            'lookup_success_location': filestore.put(os.path.join(oasis_files_dir, 'gul_summary_map.csv')),
            'lookup_validation_location': filestore.put(os.path.join(oasis_files_dir, 'exposure_summary_report.json')),
            'summary_levels_location': filestore.put(os.path.join(oasis_files_dir, 'exposure_summary_report.json')),
            'output_location': filestore.put(oasis_files_dir),
        }

    return output_params


@task(bind=True, name='cleanup_input_generation')
def cleanup_input_generation(self, params, analysis_id=None, initiator_id=None, run_data_uuid=None, slug=None):
    notify_api_task_started(analysis_id, self.request.id, slug)

    if not settings.getboolean('worker', 'KEEP_RUN_DIR', fallback=False):
        shutil.rmtree(params['target_dir'], ignore_errors=True)

        if params['user_data_dir']:
            shutil.rmtree(params['user_data_dir'], ignore_errors=True)

    return params


#
# loss generation tasks
#


def loss_generation_task(fn):
    def maybe_extract_tar(filestore_ref, dst):
        logging.info(f'filestore_ref: {filestore_ref}')
        logging.info(f'dst: {dst}')
        with filelock.FileLock(f'{dst}.lock'):
            if not Path(dst).exists():
                filestore.extract(filestore_ref, dst)

    def maybe_prepare_complex_data_files(complex_data_files, user_data_dir):
        with filelock.FileLock(f'{user_data_dir}.lock'):
            if complex_data_files:
                user_data_path = Path(user_data_dir)
                if not user_data_path.exists():
                    user_data_path.mkdir(parents=True, exist_ok=True)
                    prepare_complex_model_file_inputs(complex_data_files, str(user_data_path))

    def maybe_fetch_analysis_settings(analysis_settings_file, analysis_settings_fp):
        with filelock.FileLock(f'{analysis_settings_fp}.lock'):
            if not Path(analysis_settings_fp).exists():
                logging.info(f'analysis_settings_file: {analysis_settings_file}')
                logging.info(f'analysis_settings_fp: {analysis_settings_fp}')
                filestore.get(analysis_settings_file, analysis_settings_fp)

    def _prepare_directories(params, analysis_id, run_data_uuid, kwargs):
        params['root_data_dir'] = os.path.join(settings.get('worker', 'run_data_dir', fallback='/tmp/data'), f'analysis-{analysis_id}-{run_data_uuid}')
        Path(params['root_data_dir']).mkdir(parents=True, exist_ok=True)

        params.setdefault('oasis_fp', os.path.join(params['root_data_dir'], f'input-data'))
        params.setdefault('model_run_fp', os.path.join(params['root_data_dir'], f'run-data'))
        params.setdefault('results_path', os.path.join(params['root_data_dir'], f'results-data'))
        params.setdefault('user_data_dir', os.path.join(params['root_data_dir'], f'user-data'))
        params.setdefault('analysis_settings_fp', os.path.join(params['root_data_dir'], 'analysis_settings.json'))

        input_location = kwargs.get('input_location')
        if input_location:
            maybe_extract_tar(
                input_location,
                params['oasis_fp'],
            )

        run_location = params.get('run_location')
        if run_location:
            maybe_extract_tar(
                run_location,
                params['model_run_fp'],
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
                params['analysis_settings_fp']
            )

    def run(self, params, *args, run_data_uuid=None, analysis_id=None, **kwargs):
        if isinstance(params, list):
            for p in params:
                _prepare_directories(p, analysis_id, run_data_uuid, kwargs)
        else:
            _prepare_directories(params, analysis_id, run_data_uuid, kwargs)

        return fn(self, params, *args, analysis_id=analysis_id, **kwargs)

    return run


@task(bind=True, name='prepare_losses_generation_params')
@loss_generation_task
def prepare_losses_generation_params(
    self,
    params,
    analysis_id=None,
    slug=None,
    num_chunks=None,
    **kwargs,
):
    notify_api_task_started(analysis_id, self.request.id, slug)

    model_id = settings.get('worker', 'model_id')
    config_path = get_oasislmf_config_path(model_id)
    config = get_json(config_path)

    return OasisManager().prepare_loss_generation_params(
        model_data_fp=os.path.join(os.path.dirname(config_path), config['model_data_dir']),
        ktools_error_guard=settings.getboolean('worker', 'KTOOLS_ERROR_GUARD', fallback=True),
        ktools_debug=settings.getboolean('worker', 'DEBUG_MODE', fallback=False),
        ktools_fifo_queue_dir=os.path.join(params['model_run_fp'], 'fifo'),
        ktools_work_dir=os.path.join(params['model_run_fp'], 'work'),
        ktools_alloc_rule_gul=settings.get('worker', 'KTOOLS_ALLOC_RULE_GUL', fallback=None),
        ktools_alloc_rule_il=settings.get('worker', 'KTOOLS_ALLOC_RULE_IL', fallback=None),
        ktools_alloc_rule_ri=settings.get('worker', 'KTOOLS_ALLOC_RULE_RI', fallback=None),
        ktools_num_processes=num_chunks,
        **params,
    )


@task(bind=True, name='prepare_losses_generation_directory')
@loss_generation_task
def prepare_losses_generation_directory(self, params, analysis_id=None, slug=None, **kwargs):
    notify_api_task_started(analysis_id, self.request.id, slug)

    params['analysis_settings'] = OasisManager().prepare_run_directory(**params)

    # store the run dir in the file store
    params['run_location'] = filestore.put(params['model_run_fp'])

    return params


@task(bind=True, name='generate_losses_chunk')
@loss_generation_task
def generate_losses_chunk(self, params, chunk_idx, num_chunks, analysis_id=None, slug=None, **kwargs):
    notify_api_task_started(analysis_id, self.request.id, slug)

    chunk_params = {
        **params,
        'script_fp': f'{params["script_fp"]}.{chunk_idx}',
        'ktools_fifo_queue_dir': os.path.join(params['model_run_fp'], 'fifo'),
        'ktools_work_dir': os.path.join(params['model_run_fp'], 'work/'),
    }

    Path(chunk_params['ktools_work_dir']).mkdir(parents=True, exist_ok=True)
    Path(chunk_params['ktools_fifo_queue_dir']).mkdir(parents=True, exist_ok=True)

    params['fifo_queue_dir'], params['bash_trace'] = OasisManager().run_loss_generation(**chunk_params)

    return {
        **params,
        'chunk_work_location': filestore.put(params['ktools_work_dir']),
        'chunk_script_path': chunk_params['script_fp'],
        'process_number': chunk_idx + 1,
    }


@task(bind=True, name='generate_losses_output')
@loss_generation_task
def generate_losses_output(self, params, analysis_id=None, slug=None, **kwargs):
    notify_api_task_started(analysis_id, self.request.id, slug)
    res = {**params[0]}

    abs_fifo_dir = os.path.join(
        res['model_run_fp'],
        res['ktools_fifo_queue_dir'],
    )
    Path(abs_fifo_dir).mkdir(exist_ok=True, parents=True)

    abs_work_dir = os.path.join(
        res['model_run_fp'],
        res['ktools_work_dir'],
    )
    Path(abs_work_dir).mkdir(exist_ok=True, parents=True)

    # collect the run results
    for p in params:
        with TemporaryDir() as d:
            filestore.extract(p['chunk_work_location'], d)

            merge_dirs(os.path.join(d, 'work'), abs_work_dir)
            merge_dirs(os.path.join(d, 'fifo'), abs_fifo_dir)

    OasisManager().run_loss_outputs(**res)
    res['bash_trace'] = '\n\n'.join(
        f'Analysis Chunk {idx}:\n{chunk["bash_trace"]}' for idx, chunk in enumerate(params)
    )

    return {
        **res,
        'output_location': filestore.put(os.path.join(res['model_run_fp'], 'output')),
        'log_location': filestore.put(os.path.join(res['model_run_fp'], 'log')),
    }


@task(bind=True, name='cleanup_losses_generation')
def cleanup_losses_generation(self, params, analysis_id=None, slug=None, **kwargs):
    notify_api_task_started(analysis_id, self.request.id, slug)

    if not settings.getboolean('worker', 'KEEP_RUN_DIR', fallback=False):
        shutil.rmtree(params['root_run_dir'], ignore_errors=True)

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
