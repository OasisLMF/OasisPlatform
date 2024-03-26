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
]

import logging
import json
import os
import tempfile
import shutil
import subprocess
from copy import deepcopy

from pathlib2 import Path
from oasislmf import __version__ as mdk_version
from oasislmf.utils.exceptions import OasisException

from ..common.data import ORIGINAL_FILENAME, STORED_FILENAME


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

        if filestore._is_locally_stored(stored_fn):
            # If refrence is local filepath check that it exisits and copy/symlink
            from_path = filestore.filepath(stored_fn)
            to_path = os.path.join(run_directory, orig_fn)
            if os.name == 'nt':
                logging.info(f'complex_model_file: copy {from_path} to {to_path}')
                shutil.copy(from_path, to_path)
            else:
                logging.info(f'complex_model_file: link {from_path} to {to_path}')
                os.symlink(from_path, to_path)
        else:
            # If reference is a remote, then download the file & rename to 'original_filename'
            fpath = filestore.get(stored_fn, run_directory)
            shutil.move(fpath, os.path.join(run_directory, orig_fn))
