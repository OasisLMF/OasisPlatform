__all__ = [
    'LoggingTaskContext',
    'log_params',
    'paths_to_absolute_paths',
    'TemporaryDir',
    'get_oasislmf_config_path',
    'get_model_settings',
    'get_worker_versions',
    'InvalidInputsException',
    'MissingModelDataException',
    'prepare_complex_model_file_inputs',
    'config_strip_default_exposure',
    'unwrap_task_args',
    'get_lookup_success_file',
    'run_oasis',
    'run_function',
    'get_keys_format',
    'load_subject_at_risk_data',
    'split_subject_at_risk_data',
    'store_subject_at_risk_chunks',
    'load_subject_at_risk_chunk',
    'generate_chunk_keys',
    'merge_dataframes',
    'take_first',

    'notify_api_status_v1',
    'notify_api_status_v2',
    'notify_subtask_status_v2',
]

import functools
import logging
import json
import os
import pathlib
import tempfile
import shutil
import threading
from datetime import datetime
from copy import deepcopy
from celery import signature

import numpy as np
import pandas as pd
from pathlib2 import Path
from oasislmf import __version__ as mdk_version
from ods_tools import __version__ as ods_version
from oasislmf.utils.exceptions import OasisException

from ..common.data import ORIGINAL_FILENAME, STORED_FILENAME
from .oasis_subprocess_runner import MANAGER, run_in_subprocess, subprocess_enabled
import requests


logger = logging.getLogger(__name__)


# Send notification back to the API Once task is read from Queue
def run_oasis(method, **kwargs):
    """Run `OasisManager().<method>(**kwargs)`.

    On threads/gevent/eventlet workers (or when `OASIS_WORKER_SUBPROCESS_EXECUTION`
    says so) it runs in a separate, killable process, so cancelling the task stops it
    (see `oasis_subprocess_runner`). Otherwise it's called in-process.
    """
    if subprocess_enabled():
        return run_in_subprocess(MANAGER, kwargs, method=method)
    from oasislmf.manager import OasisManager
    return getattr(OasisManager(), method)(**kwargs)


def run_function(func, in_process_only=None, **kwargs):
    """ Call `func(**kwargs)`, in a separate killable process when `subprocess_enabled()`
        (like `run_oasis`). `func` must be importable without the celery app (e.g. from
        this module) and `kwargs` JSON serialisable.

        `in_process_only`: extra kwargs, e.g. the task's filestore, only passed when
        `func` is called in-process. `func` must default them itself.
    """
    if subprocess_enabled():
        return run_in_subprocess(f'{func.__module__}:{func.__qualname__}', kwargs)
    return func(**kwargs, **(in_process_only or {}))


def notify_api_status_v1(analysis_pk, task_status):
    logger.info("Notify API: analysis_id={}, status={}".format(
        analysis_pk,
        task_status
    ))
    signature(
        'set_task_status',
        args=(analysis_pk, task_status),
        queue='celery'
    ).delay()


def notify_api_status_v2(analysis_pk, task_status):
    logger.info("Notify API: analysis_id={}, status={}".format(
        analysis_pk,
        task_status
    ))
    signature(
        'set_task_status_v2',
        args=(analysis_pk, task_status, datetime.now().timestamp()),
        queue='celery-v2'
    ).delay()


def notify_subtask_status_v2(analysis_id, initiator_id, task_slug, subtask_status, error_msg=''):
    logger.info(f"Notify API: analysis_id={analysis_id}, task_slug={task_slug}  status={subtask_status}, error={error_msg}")
    signature(
        'set_subtask_status',
        args=(analysis_id, initiator_id, task_slug, subtask_status, error_msg),
        queue='celery-v2'
    ).delay()


class TaskLogFilter(logging.Filter):
    """Block infrastructure loggers from flooding task logs at DEBUG level.

    Allows all task-relevant loggers (oasislmf and its dependencies) through
    while suppressing unrelated infrastructure packages.
    """
    BLOCKED = (
        'psycopg', 'django', 'celery', 'kombu', 'amqp',
        'billiard', 'urllib3', 'boto3', 'botocore', 'azure',
        'numba',
    )

    def filter(self, record):
        if any(record.name == b or record.name.startswith(b + '.') for b in self.BLOCKED):
            return record.levelno >= logging.INFO
        return True


class _ThreadScopedFilter(logging.Filter):
    """ Restricts a handler to records from the thread that installed it.

        The root logger is shared process-wide, so under a thread-based Celery
        pool multiple tasks can have their own FileHandler attached to it at
        once; without this, every handler receives every thread's records.
    """

    def __init__(self):
        super().__init__()
        self.thread_id = threading.get_ident()

    def filter(self, record):
        return record.thread == self.thread_id


def _level_to_int(level):
    return level if isinstance(level, int) else logging.getLevelNamesMapping()[level]


class _LevelTracker:
    """ Tracks concurrently active level requests per logger, so one task
        finishing early can't drop the effective level out from under a
        still-running sibling task using the same logger.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._state = {}  # logger -> (baseline_level, [requested_levels])

    def acquire(self, logger, level):
        numeric_level = _level_to_int(level)
        with self._lock:
            baseline, requests = self._state.setdefault(logger, (logger.level, []))
            requests.append(numeric_level)
            logger.setLevel(min(requests))

    def release(self, logger, level):
        numeric_level = _level_to_int(level)
        with self._lock:
            baseline, requests = self._state[logger]
            requests.remove(numeric_level)
            if requests:
                logger.setLevel(min(requests))
            else:
                logger.setLevel(baseline)
                del self._state[logger]


_level_tracker = _LevelTracker()


class LoggingTaskContext:
    """ Adds a file log handler to the root logger and pushes a copy all logs to
        the 'log_filename'

        Docs: https://docs.python.org/3/howto/logging-cookbook.html#using-a-context-manager-for-selective-logging
    """

    def __init__(self, logger, log_filename, level=None, close=True, delete_on_exit=True):
        self.logger = logger
        self.level = level
        self.log_filename = log_filename
        self.close = close
        # 'w' (truncate) rather than the FileHandler default of 'a' (append) - on a
        # failed task the file is deliberately left on disk for 'task_failure' to
        # upload (see __exit__ below); if the task is then retried by celery, that
        # retry must not append onto the previous failed attempt's leftover content.
        self.handler = logging.FileHandler(log_filename, mode='w')
        self.handler.addFilter(_ThreadScopedFilter())
        self.delete_on_exit = delete_on_exit
        self._filter = None

    def __enter__(self):
        if self.level:
            self.handler.setLevel(self.level)
            _level_tracker.acquire(self.logger, self.level)
            if _level_to_int(self.level) <= logging.DEBUG:
                self._filter = TaskLogFilter()
                self.logger.addFilter(self._filter)
        if self.handler:
            self.logger.addHandler(self.handler)

    def __exit__(self, et, ev, tb):
        if self.level:
            _level_tracker.release(self.logger, self.level)
            if self._filter:
                self.logger.removeFilter(self._filter)
        if self.handler:
            self.logger.removeHandler(self.handler)
        if self.handler and self.close:
            self.handler.close()
        # On failure leave the log file in place - 'task_failure' handlers read it
        # from disk (after the context manager has exited) to attach the full
        # output (including kernel STDOUT/STDERR) to the failed task/analysis.
        if os.path.isfile(self.log_filename) and self.delete_on_exit and et is None:
            os.remove(self.log_filename)


def log_params(params, kwargs, exclude_keys=[]):
    if isinstance(params, list):
        params = params[0]
    print_params = {k: params[k] for k in set(list(params.keys())) - set(exclude_keys)}
    logging.info('task params: \nparams={}, \nkwargs={}'.format(
        json.dumps(print_params, indent=2),
        json.dumps(kwargs, indent=2),
    ))


def paths_to_absolute_paths(dictionary, config_path=''):
    basedir = os.path.dirname(config_path)
    if not isinstance(dictionary, dict):
        raise ValueError("Input must be a dictionary.")

    params = deepcopy(dictionary)
    for key, value in dictionary.items():
        # If the value is a string and exists as a path, convert it to absolute path
        if isinstance(value, str):
            path_value = os.path.join(basedir, value)
            if os.path.exists(path_value):
                params[key] = os.path.abspath(path_value)
        # if value is 'None' remote it
        elif value is None:
            del params[key]
    return params


def config_strip_default_exposure(config):
    """ Safeguard to make sure any 'oasislmf.json' files have platform default stripped out
    """
    exclude_list = [
        'oed_location_csv',
        'oed_accounts_csv',
        'oed_info_csv',
        'oed_scope_csv',
        'analysis_settings_json',
        'reporting_currency',
        'currency_conversion_json'
    ]
    return {k: v for k, v in config.items() if k not in exclude_list}


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
            shutil.rmtree(self.name, ignore_errors=True)


def get_oasislmf_config_path(settings, model_id=None):
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


def get_model_settings(settings):
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


def get_oed_version():
    try:
        from ods_tools.oed.oed_schema import OedSchema
        OedSchemaData = OedSchema.from_oed_schema_info(oed_schema_info=os.environ.get('OASIS_OED_SCHEMA_INFO', None))
        return OedSchemaData.schema['version']
    except Exception:
        logging.exception("Failed to get OED version info")
        return None


def get_worker_versions():
    """ Search and return the versions of Oasis components
    """
    ktool_ver_str = 'pytools'
    plat_ver_file = '/home/worker/VERSION'
    oed_schma_ver = get_oed_version()

    if os.path.isfile(plat_ver_file):
        with open(plat_ver_file, 'r') as f:
            plat_ver_str = f.read().strip()
    else:
        plat_ver_str = ""

    return {
        "oasislmf": mdk_version,
        "ktools": ktool_ver_str,
        "platform": plat_ver_str,
        "ods-tools": ods_version,
        "oed-schema": oed_schma_ver,
    }


class InvalidInputsException(OasisException):
    def __init__(self, input_archive):
        super(InvalidInputsException, self).__init__('Inputs location not a tarfile: {}'.format(input_archive))


class MissingModelDataException(OasisException):
    def __init__(self, model_data_path):
        super(MissingModelDataException, self).__init__('Model data not found: {}'.format(model_data_path))


def merge_dirs(src_root, dst_root):
    for root, dirs, files in os.walk(src_root):
        for f in files:
            src = os.path.join(root, f)
            rel_dst = os.path.relpath(src, src_root)
            abs_dst = os.path.join(dst_root, rel_dst)
            Path(abs_dst).parent.mkdir(exist_ok=True, parents=True)
            shutil.copy(os.path.join(root, f), abs_dst)


def unwrap_task_args(task_args):
    """ Takes the args of a celery task return, and rolls back the nesting to the
        first dict found, then return dict by value

        called_params = unwrap_task_args(kwargs.get('args'))
    """
    value = task_args
    while isinstance(value, list) and value:
        value = value[0]
    return deepcopy(value) if isinstance(value, dict) else {}


def prepare_complex_model_file_inputs(complex_model_files, run_directory, filestore):
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

        fpath = filestore.get(stored_fn, run_directory)
        shutil.move(fpath, os.path.join(run_directory, orig_fn))


def update_params(params, given_params):
    """
    Changes exposure run's given parameters.
    """
    ALLOWED_PARAMS = [
        'kernel_alloc_rule_il',
        'model_perils_covered',
        'loss_factor',
        'supported_oed_coverage_types',
        'fmpy_sort_output',
        'fmpy_low_memory',
        'extra_summary_cols',
        'kernel_alloc_rule_ri',
        'check_oed',
        'disaggregation',
        'verbose'
    ]
    for k, v in given_params.items():
        if k in ALLOWED_PARAMS:
            params[k] = v
    if 'disaggregation' not in given_params and given_params.get('do_disaggregation') is not None:
        params['disaggregation'] = 'items' if given_params['do_disaggregation'] else 'none'
    if params['supported_oed_coverage_types'] == [0]:
        params['supported_oed_coverage_types'] = None
    params["output_file"] = "outfile.csv"


def copy_or_download(source, destination):
    """
    Gets files needed into the storage they need to be in.

    Local storage backends hand back a filesystem path, which is copied directly.
    Remote backends (S3, Azure, GCS, ...) hand back a pre-authenticated HTTP(S) URL
    (e.g. an S3 presigned URL or Azure SAS URL), which is fetched with a plain GET
    rather than a backend-specific SDK call.
    """
    if not source:
        return
    if not source.startswith("http"):
        shutil.copy2(source, destination)
        return
    with requests.get(source, stream=True) as response:
        response.raise_for_status()
        with open(destination, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)


def get_lookup_success_file(directory):
    """Returns the path of the gul summary map stored as the analysis `lookup_success_file`,
    written as parquet by newer versions of oasislmf and as csv by older ones

    Args:
        directory: generated oasis files directory

    Returns:
        (path) path of the summary map, None if not found
    """
    for filename in ['gul_summary_map.parquet', 'gul_summary_map.csv']:
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            return filepath
    return None


def get_destination_file(filename, destination_dir, destination_title):
    """Returns desired location for file to go into as csv, parquet, tar.gz, tar.zst
    (does not move the file itself!)

    Args:
        filename: name of file existing
        destination_dir: dir to send file to
        destination_title: name to store as

    Raises:
        ValueError: file is not csv or parquet

    Returns:
        (path) path for file

    """
    _, ext = os.path.splitext(filename)
    if ext.startswith('.csv'):  # Some can be stored like '.csv_abc4def'
        return os.path.join(destination_dir, destination_title + ".csv")
    if ext.startswith('.parquet'):
        return os.path.join(destination_dir, destination_title + ".parquet")
    if ext.startswith('.gz'):
        return os.path.join(destination_dir, destination_title + '.tar.gz')
    if ext.startswith('.zst'):
        return os.path.join(destination_dir, destination_title + '.tar.zst')
    raise ValueError(f"File must be either Parquet, CSV, tar.gz, tar.zst: {filename, ext}")


def get_all_exposure_files(loc_filepath, acc_filepath, ri_filepath, rl_filepath, conv_filepath, directory):
    """Gets all files required and puts them in directory

    Args:
        loc_filepath: filepath to find location file at
        acc_filepath: filepath to find accounts file at
        ri_filepath: filepath to find reinsurance info file at
        rl_filepath: filepath to find reinsurance loss file at
        conv_filepath: filepath to find currency_converion.json at
        directory: place all files moved to

    Returns:
        (file, file, file, file, file): files in order of arguments
    """
    loc_temp = acc_temp = ri_temp = rl_temp = conv_temp = None
    if loc_filepath:
        loc_temp = get_destination_file(loc_filepath, directory, "location")
        copy_or_download(loc_filepath, loc_temp)
    if acc_filepath:
        acc_temp = get_destination_file(acc_filepath, directory, "account")
        copy_or_download(acc_filepath, acc_temp)
    if ri_filepath:
        ri_temp = get_destination_file(ri_filepath, directory, "ri_info")
        copy_or_download(ri_filepath, ri_temp)
    if rl_filepath:
        rl_temp = get_destination_file(rl_filepath, directory, "ri_scope")
        copy_or_download(rl_filepath, rl_temp)
    if conv_filepath:
        conv_temp = os.path.join(directory, "currency_conversion.json")
        copy_or_download(conv_filepath, conv_temp)
    return (loc_temp, acc_temp, ri_temp, rl_temp, conv_temp)


# --- keys generation (lookup) helpers, used by distributed_tasks ------------ #
# Kept free of the celery app so they can also run in a subprocess (`run_function`).

KEYS_FORMAT_EXT = {'parquet': 'parquet', 'oasis': 'csv'}


@functools.lru_cache(maxsize=None)
def _worker_filestore():
    """ The worker's filestore, built from its settings (as `distributed_tasks.filestore`) """
    from ..common.filestore.filestore import get_filestore
    from ..conf.iniconf import settings
    return get_filestore(settings)


def load_subject_at_risk_data(params):
    """ Returns the subject at risk (SAR) exposure as a DataFrame, with 'loc_id' assigned

    The SAR source depends on the class of business: the location file for
    property / marine, but the account file for cyber / liability, which can be
    run with no location file at all. Both files are loaded (when present) so the
    class of business is detected the same way as in `write_input_files`.
    """
    from ods_tools.oed.exposure import OedExposure

    def _abs_path(key):
        return pathlib.Path(os.path.abspath(params[key])) if params.get(key) else None

    exposure = OedExposure(
        location=_abs_path('oed_location_csv'),
        account=_abs_path('oed_accounts_csv'),
        oed_schema_info=params.get('oed_schema_info') or os.environ.get("OASIS_OED_SCHEMA_INFO", None),
        check_oed=params.get('check_oed', True),
        use_field=True,
        backend_dtype=params.get('oed_backend_dtype', 'pd_dtype'),
        disable_oed_version_update=params.get('disable_oed_version_update', False),
    )

    try:
        # Oasislmf 2.4.x
        from oasislmf.utils.data import prepare_oed_exposure
        prepare_oed_exposure(exposure)
    except ImportError:
        # Fallback Oasislmf LTS 2.3.x, LTS 1.28.x (location based models only)
        from oasislmf.utils.data import prepare_location_df
        exposure.location.dataframe = prepare_location_df(exposure.location.dataframe)
        return exposure.location.dataframe

    return exposure.get_subject_at_risk_source().dataframe


def subject_at_risk_chunk_rows(sar_df, num_chunks):
    """ Returns the row positions of `sar_df` in each of its `num_chunks` lookup chunks

    Split by subject id ('loc_id') rather than by row, so that every row for a
    subject (e.g. multiple layers of a cyber account) is looked up in the same chunk.
    The subjects, in order of first appearance, are split into `num_chunks` even
    blocks, and each row is assigned its chunk in one pass.
    """
    codes, sar_ids = pd.factorize(sar_df['loc_id'], use_na_sentinel=False)
    chunk_sizes = [len(ids) for ids in np.array_split(np.arange(len(sar_ids)), num_chunks)]
    row_chunks = np.repeat(np.arange(num_chunks), chunk_sizes)[codes]

    # stable, so rows keep their original order within each chunk
    rows = np.argsort(row_chunks, kind='stable')
    return np.split(rows, np.searchsorted(row_chunks[rows], np.arange(1, num_chunks)))


def split_subject_at_risk_data(sar_df, num_chunks, chunk_idx):
    """ Returns the `chunk_idx` slice of `sar_df`, split into `num_chunks` parts
        (see `subject_at_risk_chunk_rows`)
    """
    chunk_rows = subject_at_risk_chunk_rows(sar_df, num_chunks)[chunk_idx]
    return sar_df.iloc[chunk_rows].reset_index(drop=True)


def store_subject_at_risk_chunks(params, num_chunks, chunks_dir, filestore=None):
    """ Load the SAR exposure once, split it into `num_chunks` parquet files and
        store them, returning one filestore reference per lookup chunk

        Without this every 'prepare_keys_file_chunk' task loads and checks the
        whole portfolio just to keep its own rows, so lookup memory and CPU grow
        with the chunk count.

        `filestore` defaults to the worker's (built from its settings), e.g. when
        run in a subprocess.
    """
    filestore = filestore or _worker_filestore()
    sar_df = load_subject_at_risk_data(params)

    chunk_refs = []
    for chunk_idx, chunk_rows in enumerate(subject_at_risk_chunk_rows(sar_df, num_chunks)):
        chunk_fp = os.path.join(chunks_dir, f'sar-chunk-{chunk_idx + 1}.parquet')
        chunk_df = sar_df.iloc[chunk_rows].reset_index(drop=True)
        chunk_df.to_parquet(chunk_fp, index=False)
        chunk_refs.append(filestore.put(
            chunk_fp,
            filename=os.path.basename(chunk_fp),
            subdir=params['storage_subdir']
        ))
        os.remove(chunk_fp)
    return chunk_refs


def load_subject_at_risk_chunk(params, num_chunks, chunk_idx, filestore=None):
    """ Returns this lookup chunk's SAR rows, from the file stored by
        'pre_analysis_hook' when there is one, otherwise by loading and splitting
        the full exposure (e.g. the API didn't send 'num_chunks' to the hook)

        The chunk file is read straight from the filestore, as 'filestore.get'
        on S3 / Azure also leaves a copy in the worker's data cache. `filestore`
        defaults to the worker's (built from its settings).
    """
    sar_chunks = params.get('sar_chunks') or []
    if len(sar_chunks) != num_chunks:
        if sar_chunks:
            logger.warning(f'Expected {num_chunks} pre-split exposure chunks, got {len(sar_chunks)}, loading the full exposure')
        elif num_chunks > 1:
            logger.info('No pre-split exposure chunks, loading the full exposure')
        return split_subject_at_risk_data(load_subject_at_risk_data(params), num_chunks, chunk_idx)

    with (filestore or _worker_filestore()).open(sar_chunks[chunk_idx], 'rb') as f:
        return pd.read_parquet(f)


def get_keys_format(params):
    """ Return the oasislmf 'keys_format' and matching file extension for the
        distributed lookup. Chunk merging only supports the tabular formats, so
        'json' falls back to the default, 'parquet'.
    """
    keys_format = (params.get('keys_format') or 'parquet').lower()
    if keys_format not in KEYS_FORMAT_EXT:
        logger.warning(f'keys_format "{keys_format}" is not supported for distributed lookups, using "parquet"')
        keys_format = 'parquet'
    return keys_format, KEYS_FORMAT_EXT[keys_format]


def generate_chunk_keys(params, num_chunks, chunk_idx, chunk_target_dir, filestore=None):
    """ Run the keys lookup for one chunk of the exposure, writing its keys files
        to `chunk_target_dir` (the body of the 'prepare_keys_file_chunk' task).
    """
    from oasislmf.preparation.lookup import OasisLookupFactory
    _, lookup = OasisLookupFactory.create(
        lookup_config_fp=params.get('lookup_config_json', None),
        model_keys_data_path=params.get('lookup_data_dir', None),
        model_version_file_path=params.get('model_version_csv', None),
        lookup_module_path=params.get('lookup_module_path', None),
        complex_lookup_config_fp=params.get('lookup_complex_config_json', None),
        user_data_dir=params.get('user_data_dir', None),
        output_directory=chunk_target_dir,
    )

    sar_df = load_subject_at_risk_chunk(params, num_chunks, chunk_idx, filestore=filestore)

    # With no location file the chunk count isn't capped by the row count
    # (see `_get_inputs_generation_chunks`), so a chunk can be empty. Skip the
    # lookup, `collect_keys` merges whatever the other chunks produced.
    if sar_df.empty:
        logger.info(f'Lookup chunk {chunk_idx + 1}/{num_chunks} is empty --skipped--')
    else:
        keys_format, keys_ext = get_keys_format(params)
        chunk_keys_fp = os.path.join(chunk_target_dir, f'keys.{keys_ext}')
        chunk_keys_errors_fp = os.path.join(chunk_target_dir, f'keys-errors.{keys_ext}')
        lookup.generate_key_files(
            location_fp=None,
            location_df=sar_df,
            successes_fp=chunk_keys_fp,
            errors_fp=chunk_keys_errors_fp,
            output_format=keys_format,
            keys_success_msg=False,
            multiproc_enabled=params.get('lookup_multiprocessing', False),
            multiproc_num_cores=params.get('lookup_num_processes', -1),
            multiproc_num_partitions=params.get('lookup_num_chunks', -1),
        )


def _merge_csv_streaming(paths, output_file):
    import polars as pl
    # scan_csv errors on a zero-byte file, so skip those first.
    non_empty_paths = []
    for path in paths:
        if os.path.getsize(path) > 0:
            non_empty_paths.append(str(path))  # polars mishandles pathlib2.Path
        else:
            logger.info(f"File {path} is empty. --skipped--")
    if not non_empty_paths:
        logger.warning(f"All files were empty: {paths}. --skipped--")
        return

    # diagonal concat: chunk files' column sets aren't always identical.
    # relaxed: a header-only chunk scans as all-String, so dtypes can differ too.
    lazy_frames = [pl.scan_csv(path) for path in non_empty_paths]
    (
        pl.concat(lazy_frames, how='diagonal_relaxed')
        .unique(keep='first', maintain_order=True)
        .sink_csv(str(output_file))
    )


def _merge_parquet_streaming(paths, output_file):
    import polars as pl
    import pyarrow as pa
    import pyarrow.parquet as pq
    # Dedup by content, not index - chunk files carry no meaningful index.
    valid_paths = []
    for path in paths:
        try:
            pq.ParquetFile(path).schema_arrow
            valid_paths.append(str(path))
        except pa.lib.ArrowInvalid:
            logger.info(f"File {path} is empty or unreadable. --skipped--")
    if not valid_paths:
        logger.warning(f"All files were empty or unreadable: {paths}. --skipped--")
        return

    # relaxed: a zero-row chunk written from pandas has all-null column types.
    lazy_frames = [pl.scan_parquet(path) for path in valid_paths]
    (
        pl.concat(lazy_frames, how='diagonal_relaxed')
        .unique(keep='first', maintain_order=True)
        .sink_parquet(str(output_file))
    )


def merge_dataframes(paths, output_file, file_type):
    if not paths:
        logger.warning("merge_dataframes was called with an empty path list.")
        return
    if file_type == 'csv':
        _merge_csv_streaming(paths, output_file)
    elif file_type == 'parquet':
        _merge_parquet_streaming(paths, output_file)


def take_first(paths, output_file):
    first_path = paths[0]
    logger.info(f"Using {first_path} and ignoring others.")
    shutil.copy2(first_path, output_file)
