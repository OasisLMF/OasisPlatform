import inspect
import logging
import json
import os
import shutil
import tarfile
import time
import sys

from celery import Celery
from celery.task import task
from ConfigParser import ConfigParser

'''
Celery task wrapper for Oasis ktools calculation.
'''

CONFIG_PARSER = ConfigParser()
CURRENT_DIRECTORY = \
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(CURRENT_DIRECTORY, ".."))
INI_PATH = os.path.abspath(os.path.join(CURRENT_DIRECTORY, 'Tasks.ini'))
CONFIG_PARSER.read(INI_PATH)

from oasis_utils import oasis_utils, oasis_log_utils

INPUTS_DATA_DIRECTORY = CONFIG_PARSER.get('Default', 'INPUTS_DATA_DIRECTORY')
OUTPUTS_DATA_DIRECTORY = CONFIG_PARSER.get('Default', 'OUTPUTS_DATA_DIRECTORY')
MODEL_DATA_DIRECTORY = CONFIG_PARSER.get('Default', 'MODEL_DATA_DIRECTORY')
WORKING_DIRECTORY = CONFIG_PARSER.get('Default', 'WORKING_DIRECTORY')

KTOOLS_BATCH_COUNT = int(os.environ.get("KTOOLS_BATCH_COUNT")) or -1

ARCHIVE_FILE_SUFFIX = '.tar'

CELERY = Celery()
CELERY.config_from_object('common.CeleryConfig')

logging.info("Started worker")
logging.info("INPUTS_DATA_DIRECTORY: {}".format(INPUTS_DATA_DIRECTORY))
logging.info("OUTPUTS_DATA_DIRECTORY: {}".format(OUTPUTS_DATA_DIRECTORY))
logging.info("MODEL_DATA_DIRECTORY: {}".format(MODEL_DATA_DIRECTORY))
logging.info("WORKING_DIRECTORY: {}".format(WORKING_DIRECTORY))
logging.info("KTOOLS_BATCH_COUNT: {}".format(KTOOLS_BATCH_COUNT))

@task(name='run_analysis', bind=True)
def start_analysis_task(self, input_location, analysis_settings_json):
    '''
    Task wrapper for running an analysis.
    Args:
        analysis_profile_json (string): The analysis settings.
    Returns:
        (string) The location of the outputs.
    '''
    try:

        logging.info("INPUTS_DATA_DIRECTORY: {}".format(INPUTS_DATA_DIRECTORY))
        logging.info("OUTPUTS_DATA_DIRECTORY: {}".format(OUTPUTS_DATA_DIRECTORY))
        logging.info("MODEL_DATA_DIRECTORY: {}".format(MODEL_DATA_DIRECTORY))
        logging.info("WORKING_DIRECTORY: {}".format(WORKING_DIRECTORY))
        logging.info("KTOOLS_BATCH_COUNT: {}".format(KTOOLS_BATCH_COUNT))

        self.update_state(state=oasis_utils.STATUS_RUNNING)
        output_location = start_analysis(
            analysis_settings_json[0],
            input_location)
    except Exception as e:
        logging.exception("Model execution task failed.")
        raise e

    return output_location


def get_current_module_directory():
    ''' Get the directory of the current module.'''
    return os.path.dirname(
        os.path.abspath(inspect.getfile(inspect.currentframe())))

@oasis_log_utils.oasis_log()
def start_analysis(analysis_settings, input_location):
    '''
    Run an analysis.
    Args:
        analysis_profile_json (string): The analysis settings.
    Returns:
        (string) The location of the outputs.
    '''
    os.chdir(WORKING_DIRECTORY)

    #
    # Set up the following directory structure:
    # - WORKING_DIRECTORY
    # |-Analysis working directory
    #   |-static  (soft-link to model files)
    #   |-input   (upload repository)
    #   |-output  (model results will be written into
    #   |          this folder then archived to the
    #   |          download directory)
    #   |-fifo (scratch directory for named pipes)
    #   |-work (scratch directory for intermediate files)
    #

    # Check that the input archive exists and is valid
    input_archive = os.path.join(
        INPUTS_DATA_DIRECTORY,
        input_location + ARCHIVE_FILE_SUFFIX)
    if not os.path.exists(input_archive):
        raise Exception("Inputs location not found: {}".format(input_archive))
    if not tarfile.is_tarfile(input_archive):
        raise Exception(
            "Inputs location not a tarfile: {}".format(input_archive))

    source_tag = \
        analysis_settings['analysis_settings']['source_tag']
    analysis_tag = \
        analysis_settings['analysis_settings']['analysis_tag']
    logging.info(
        "Source tag = {}; Analysis tag: {}".format(
            analysis_tag, source_tag))

    module_supplier_id = \
        analysis_settings['analysis_settings']['module_supplier_id']
    model_version_id = \
        analysis_settings['analysis_settings']['model_version_id']
    logging.info(
        "Model supplier - version = {} {}".format(
            module_supplier_id, model_version_id))

    # Get the supplier module and call it
    if not os.path.exists(os.path.join(
            get_current_module_directory(),
            module_supplier_id)):
        raise Exception("Supplier module not found.")
    model_data_path = \
        os.path.join(MODEL_DATA_DIRECTORY,
                     module_supplier_id,
                     model_version_id)
    if not os.path.exists(model_data_path):
        raise Exception("Model data not found: {}".format(model_data_path))

    logging.info("Setting up analysis working directory")

    directory_name = "{}_{}_{}".format(
        source_tag, analysis_tag, oasis_utils.generate_unique_filename())
    working_directory = \
        os.path.join(WORKING_DIRECTORY, directory_name)
    os.mkdir(working_directory)
    os.mkdir(os.path.join(working_directory, "work"))
    os.mkdir(os.path.join(working_directory, "fifo"))
    output_directory = os.path.join(working_directory, "output")
    os.mkdir(output_directory)

    with tarfile.open(input_archive) as input_tarfile:
        input_tarfile.extractall(
            path=(os.path.join(working_directory, 'input')))
    if not os.path.exists(os.path.join(working_directory, 'input')):
        raise Exception("Input archive did not extract correctly")

    os.symlink(model_data_path, os.path.join(working_directory, "static"))

    # If an events file has not been included in the analysis input,
    # then use the default file with all events from the model data.
    analysis_events_filepath = os.path.join(working_directory, 'input', 'events.bin')
    model_data_events_filepath = os.path.join(working_directory, 'static', 'events.bin')
    if not os.path.exists(analysis_events_filepath):
        logging.info("Using default events.bin")
        shutil.copyfile(model_data_events_filepath, analysis_events_filepath)

    # If a return periods file has not been included in the analysis input,
    # then use the default from the model data.
    analysis_returnperiods_filepath = os.path.join(
        working_directory, 'input', 'returnperiods.bin')
    model_data_returnperiods_filepath = os.path.join(
        working_directory, 'static', 'returnperiods.bin')
    if not os.path.exists(analysis_returnperiods_filepath):
        logging.info("Using default returnperiods.bin")
        shutil.copyfile(model_data_returnperiods_filepath, analysis_returnperiods_filepath)

    model_runner_module = __import__(
        "{}.{}".format(module_supplier_id, "supplier_model_runner"),
        globals(),
        locals(),
        ['run'],
        -1)

    os.chdir(working_directory)
    logging.info("Working directory = {}".format(working_directory))

    # Persist the analysis_settings
    with open("analysis_settings.json", "w") as json_file:
        json.dump(analysis_settings, json_file)

    model_runner_module.run(
        analysis_settings['analysis_settings'], KTOOLS_BATCH_COUNT)

    output_location = oasis_utils.generate_unique_filename()
    output_filepath = os.path.join(
        OUTPUTS_DATA_DIRECTORY, output_location + ARCHIVE_FILE_SUFFIX)
    with tarfile.open(output_filepath, "w:gz") as tar:
        tar.add(output_directory, arcname="output")

    os.chdir(WORKING_DIRECTORY)

    logging.info("Output location = {}".format(output_location))

    return output_location
