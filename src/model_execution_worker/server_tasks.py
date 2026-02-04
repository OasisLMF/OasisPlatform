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
from ods_tools.combine import combine
import logging
import tarfile

app = Celery()

app.config_from_object(celery_conf)


@app.task(name='run_exposure_run')
def run_exposure_run(loc_filepath, acc_filepath, ri_filepath, rl_filepath,
                     currency_conversion_json_filepath, reporting_currency, given_params):
    """
    Performs an exposure run
    Args:
        loc_filepath: path to location file or None
        acc_filepath: path to accounts file or None
        ri_filepath: path to ri file or None
        rl_filepath: path to rl file or None
        currency_conversion_json_filepath: path to currency_conversion_json or None
        reporting_currency: currency to use with currency_conversion_json or ""
        given_params: run parameters for exposure run (e.g. {'check_oed': False})
    Returns:
        (Path, Boolean): Path to exposure file or errors file, with boolean flag for success
    """
    original_dir = os.getcwd()
    with TemporaryDir() as tmpdir:
        # Put all files in dir so that reachable for OedExposure fromdir
        loc, acc, ri, rl, currency_conversion_json = get_all_exposure_files(
            loc_filepath, acc_filepath, ri_filepath, rl_filepath, currency_conversion_json_filepath, tmpdir
        )
        os.chdir(tmpdir)
        params = OasisManager()._params_run_exposure()
        params['print_summary'] = False
        update_params(params, given_params)
        if reporting_currency != "" and currency_conversion_json:
            params['currency_conversion_json'] = currency_conversion_json
            params['reporting_currency'] = reporting_currency

        logging.debug(f"Exposure run params: {params}")

        try:
            OasisManager().run_exposure(**params)
            return (get_filestore(settings).put("outfile.csv"), True)
        except Exception as e:
            with open("error.txt", "w") as error_file:
                error_file.write(str(e))
            return (get_filestore(settings).put("error.txt"), False)
        finally:
            os.chdir(original_dir)


@app.task(name='run_oed_validation')
def run_oed_validation(loc_filepath, acc_filepath, ri_filepath, rl_filepath, validation_config, currency_conversion_filepath, reporting_currency):
    """
    Performs an oed validation on the given data
    Args:
        loc_filepath: path to location file or None
        acc_filepath: path to accounts file or None
        ri_filepath: path to ri file or None
        rl_filepath: path to rl file or None
        currency_conversion_filepath: path to currency_conversion_json or None
        reporting_currency: currency to use with currency_conversion_json or ""
    Returns:
        list[str] | str: errors in validation (empty list = no errors)
    """
    with TemporaryDir() as temp_dir:
        location, account, ri_info, ri_scope, currency_conversion_json = get_all_exposure_files(
            loc_filepath, acc_filepath, ri_filepath, rl_filepath, currency_conversion_filepath, temp_dir
        )
        if reporting_currency == "" or currency_conversion_json is None:
            reporting_currency = None
            currency_conversion_json = None

        try:
            portfolio_exposure = OedExposure(
                location=location,
                account=account,
                ri_info=ri_info,
                ri_scope=ri_scope,
                validation_config=validation_config,
                currency_conversion=currency_conversion_json,
                oed_schema_info=os.environ.get("OASIS_OED_SCHEMA_INFO", None),
                reporting_currency=reporting_currency,
            )
            res = portfolio_exposure.check()
            return [str(e) for e in res]
        except Exception as e:
            logging.error(f"OED Validation failed: {str(e)}")
            return str(e)  # OdsException not JSON serializable


@app.task(name='run_exposure_transform')
def run_exposure_transform(filepath, mapping_file):
    """
    Transforms a file from one format to OED
    args:
        filepath: location of file to transform
        mapping_file: file determining how transform is made
    returns:
        (file | error, Boolean): result file/error and boolean flag for success
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

@app.task(name='run_combine_analyses')
def run_combine_analyses(input_tar_paths, output_tar_paths, config):
    """
    Combines the output of multiple analyses using ods_tools.combine.

    Note the paths at index {i} in output_tar_paths, input_tar_paths are
    considered to belong to the same analysis.

    e.g. output_tar_paths[i], input_tar_paths[i] belong to the same analysis.

    Args:
        input_tar_paths: list of paths to input tar files for each analyis
        output_tar_paths: list of paths/URLs to analysis output tar files to combine
        settings_paths: list of paths to analysis settings files
        config: combine configuration dict (validated against CombineSettingsSchema)

    Returns:
        (str, bool): Tuple of (result file path or error message, success flag)
    """
    required_input_files = ['analysis_settings.json', 'occurrence.bin']

    with TemporaryDir() as tmpdir:
        analysis_dirs = []
        for i, (_input_path, _output_path) in enumerate(zip(input_tar_paths, output_tar_paths)):
            # make analysis dir
            _curr_tmp_dir = os.path.join(tmpdir, str(i))
            os.mkdir(_curr_tmp_dir)
            os.mkdir(os.path.join(_curr_tmp_dir, 'input'))

            # download input + output tars
            _tmp_input_tar = get_destination_file(_input_path, _curr_tmp_dir, 'input')
            copy_or_download(_input_path, _tmp_input_tar)

            _tmp_output_tar = get_destination_file(_output_path, _curr_tmp_dir, 'output')
            copy_or_download(_output_path, _tmp_output_tar)

            # extract necessary files and place in correct dirs
            try:
                with tarfile.open(_tmp_input_tar, 'r:gz') as f:
                    f.extractall(path=os.path.join(_curr_tmp_dir, 'input'), members=required_input_files)
            except KeyError as e:
                logging.error('Combine input files missing: ' + str(e))
                return ('Input files missing: ' + str(e), False)

            with tarfile.open(_tmp_output_tar, 'r:gz') as f:
                f.extractall(path=_curr_tmp_dir) # tar already has `output/`

            analysis_dirs.append(_curr_tmp_dir)

        combine_results_dir = os.path.join(tmpdir, 'combine_results')

        # run combine task
        try:
            config = combine.prepare_config(config)
            combine.combine(analysis_dirs=analysis_dirs,
                            output_dir=combine_results_dir,
                            **config)
            result_ref = get_filestore(settings).put(combine_results_dir)
            return (True, result_ref)
        except Exception as e:
            logging.error('Combine failed: {str(e)}')
            return (False, e)
