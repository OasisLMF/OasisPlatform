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

    'notify_api_status',
    'notify_subtask_status',
]

import logging
import json
import os
import re
import tempfile
import shutil
import subprocess
from datetime import datetime
from copy import deepcopy
from celery import signature

from pathlib2 import Path
from oasislmf import __version__ as mdk_version
from ods_tools import __version__ as ods_version
from oasislmf.utils.exceptions import OasisException

from ..common.data import ORIGINAL_FILENAME, STORED_FILENAME
import boto3
from urllib.parse import urlparse
from ..conf.iniconf import settings


logger = logging.getLogger(__name__)





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





class LoggingTaskContext:
    """ Adds a file log handler to the root logger and pushes a copy all logs to
        the 'log_filename'

        Docs: https://docs.python.org/3/howto/logging-cookbook.html#using-a-context-manager-for-selective-logging
    """

    def __init__(self, logger, log_filename, level=None, close=True, delete_on_exit=True):
        self.logger = logger
        self.level = level
        self.prev_level = logger.level
        self.log_filename = log_filename
        self.close = close
        self.handler = logging.FileHandler(log_filename)
        self.delete_on_exit = delete_on_exit

    def __enter__(self):
        if self.level:
            self.handler.setLevel(self.level)
            self.logger.setLevel(self.level)
        if self.handler:
            self.logger.addHandler(self.handler)

    def __exit__(self, et, ev, tb):
        if self.level:
            self.logger.setLevel(self.prev_level)
        if self.handler:
            self.logger.removeHandler(self.handler)
        if self.handler and self.close:
            self.handler.close()
        if os.path.isfile(self.log_filename) and self.delete_on_exit:
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
        'analysis_settings_json'
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
        OedSchemaData = OedSchema.from_oed_schema_info(oed_schema_info=None)
        return OedSchemaData.schema['version']
    except Exception:
        logging.exception("Failed to get OED version info")
        return None


def get_ktools_version():
    ktool_ver_str = subprocess.getoutput('fmcalc -v')

    # Match version x.x.x , x.x or x
    reg_pattern = "(\d+\.)?(\d+\.)?(\d+)"
    match_ver = re.search(reg_pattern, ktool_ver_str)

    if match_ver:
        ktool_ver_str = match_ver[0]
    return ktool_ver_str


def get_worker_versions():
    """ Search and return the versions of Oasis components
    """
    ktool_ver_str = get_ktools_version()
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
        'ktools-alloc-rule-il',
        'model-perils-covered',
        'loss-factor',
        'supported-oed-coverage-types',
        'fmpy-sort-output',
        'fmpy-low-memory',
        'extra-summary-cols',
        'ktools-alloc-rule-ri',
        'reporting-currency',
        'check-oed',
        'do-disaggregation',
        'verbose'
    ]
    for k, v in given_params.items():
        if k in ALLOWED_PARAMS:
            params[k] = v

    params["output_file"] = "outfile.csv"


def copy_or_download(source, destination):
    """
    Gets files needed into the storage they need to be in.
    """
    if not source:
        return
    if not source.startswith("http"):
        shutil.copy2(source, destination)
        return
    s3 = boto3.client(
        "s3",
        endpoint_url="http://localstack-s3:4572",
        aws_access_key_id=settings.get('worker', 'AWS_ACCESS_KEY_ID', fallback='None'),
        aws_secret_access_key=settings.get('worker', 'AWS_SECRET_ACCESS_KEY', fallback=None),
    )
    parsed_url = urlparse(source)
    bucket_name = parsed_url.path.split('/')[1]
    key = "/".join(parsed_url.path.split('/')[2:])
    s3.download_file(bucket_name, key, destination)


def get_destination_file(filename, destination_dir, destination_title):
    _, ext = os.path.splitext(filename)
    if ext.startswith('.csv'):  # Some can be stored like '.csv_abc4def'
        return os.path.join(destination_dir, destination_title + ".csv")
    if ext.startswith('.parquet'):
        return os.path.join(destination_dir, destination_title + ".parquet")
    raise ValueError(f"File must be either Parquet or CSV: {filename, ext}")


def get_all_files(loc_filepath, acc_filepath, ri_filepath, rl_filepath, temp_dir):
    loc_temp = acc_temp = ri_temp = rl_temp = None
    if loc_filepath:
        loc_temp = get_destination_file(loc_filepath, temp_dir, "location")
        copy_or_download(loc_filepath, loc_temp)
    if acc_filepath:
        acc_temp = get_destination_file(acc_filepath, temp_dir, "account")
        copy_or_download(acc_filepath, acc_temp)
    if ri_filepath:
        ri_temp = get_destination_file(ri_filepath, temp_dir, "ri_loss")
        copy_or_download(ri_filepath, ri_temp)
    if rl_filepath:
        rl_temp = get_destination_file(rl_filepath, temp_dir, "ri_scope")
        copy_or_download(rl_filepath, rl_temp)
    return (loc_temp, acc_temp, ri_temp, rl_temp)
