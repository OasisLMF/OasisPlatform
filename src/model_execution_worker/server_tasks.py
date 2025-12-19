from __future__ import absolute_import

from ..conf import celeryconf_v2 as celery_conf
from ..conf.iniconf import settings
from ..common.filestore.filestore import get_filestore
from oasislmf.manager import OasisManager
from src.model_execution_worker.utils import TemporaryDir, update_params, get_destination_file, copy_or_download, get_all_exposure_files
import os
from celery import Celery
from ods_tools.oed.exposure import OedExposure
from ods_tools.odtf.controller import transform_format
import logging

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
        get_all_exposure_files(loc_filepath, acc_filepath, ri_filepath, rl_filepath, temp_dir)
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
    """
    Returns either an error (unraised) or a possibly empty list of errors
    """
    with TemporaryDir() as temp_dir:
        location, account, ri_info, ri_scope = get_all_exposure_files(loc_filepath, acc_filepath, ri_filepath, rl_filepath, temp_dir)
        portfolio_exposure = True
        portfolio_exposure = OedExposure(
            location=location,
            account=account,
            ri_info=ri_info,
            ri_scope=ri_scope,
            validation_config=validation_config,
            oed_schema_info=os.environ.get("OASIS_OED_SCHEMA_INFO", None)
        )
        try:
            res = portfolio_exposure.check()
            return [str(e) for e in res]
        except Exception as e:
            logging.error(f"OED Validation failed: {str(e)}")
            return str(e)  # OdsException not JSON serializable


@app.task(name='run_exposure_transform')
def run_exposure_transform(filepath, mapping_file):
    """
    Returns a tuple of a file and a boolean flag of success
    """
    with TemporaryDir() as temp_dir:
        local_file = get_destination_file(filepath, temp_dir, 'local_file')
        copy_or_download(filepath, local_file)
        output_file = os.path.join(temp_dir, "transform_output.csv")
        try:
            transform_format(mapping_file=mapping_file, input_file=local_file, output_file=output_file)
            result = get_filestore(settings).put(output_file)
            return (result, True)
        except Exception as e:
            return (str(e), False)
