from __future__ import absolute_import

from ..conf import celeryconf_v2 as celery_conf
from ..conf.iniconf import settings
from ..common.filestore.filestore import get_filestore
from oasislmf.manager import OasisManager
from src.model_execution_worker.utils import TemporaryDir, update_params, get_all_files
import os
from celery import Celery
from ods_tools.oed.exposure import OedExposure
from ods_tools.main import transform

app = Celery()

app.config_from_object(celery_conf)


@app.task(name='run_exposure_task')
def run_exposure_task(loc_filepath, acc_filepath, ri_filepath, rl_filepath, given_params):
    """
    Returns a tuple of a file containing either the result or an error log, and a flag
    to say whether the run was successful to update the portfolio.exposure_status
    """
    original_dir = os.getcwd()
    with TemporaryDir() as temp_dir:
        get_all_files(loc_filepath, acc_filepath, ri_filepath, rl_filepath, temp_dir)
        os.chdir(temp_dir)
        try:
            params = OasisManager()._params_run_exposure()
            params['print_summary'] = False
            update_params(params, given_params)
            OasisManager().run_exposure(**params)
            return (get_filestore(settings).put("outfile.csv"), True)
        except Exception as e:
            with open("error.txt", "w") as error_file:
                error_file.write(str(e))
            return (get_filestore(settings).put("error.txt"), False)
        finally:
            os.chdir(original_dir)


@app.task(name='run_oed_validation')
def run_oed_validation(loc_filepath, acc_filepath, ri_filepath, rl_filepath, validation_config):
    original_dir = os.getcwd()
    with TemporaryDir() as temp_dir:
        location, account, ri_info, ri_scope = get_all_files(loc_filepath, acc_filepath, ri_filepath, rl_filepath, temp_dir)
        os.chdir(temp_dir)
        portfolio_exposure = True
        portfolio_exposure = OedExposure(
            location=location,
            account=account,
            ri_info=ri_info,
            ri_scope=ri_scope,
            validation_config=validation_config
        )
        try:
            return portfolio_exposure.check()
        except Exception as e:
            return e
        finally:
            os.chdir(original_dir)


@app.task(name='run_exposure_transform')
def run_exposure_transform(filepaths, details):
    original_dir = os.getcwd()
    options = ['location', 'account', 'ri_info', 'ri_scope']
    result = [None, None, None, None]
    with TemporaryDir() as temp_dir:
        local_filepaths = get_all_files(*filepaths, temp_dir)
        try:
            os.chdir(temp_dir)
            for i, option in enumerate(options):
                if details[option]:
                    print(f"Transforming {option} file")
                    transform(format=details['mapping_direction'], input_file=local_filepaths[i], output_file=f"{option}_transform.csv")
                    result[i] = get_filestore(settings).put(f"{option}_transform.csv")
                    print(f"{option} file transformed")
        finally:
            os.chdir(original_dir)

    return result
