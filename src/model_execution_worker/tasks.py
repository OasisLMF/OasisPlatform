import inspect
import json
import logging
import os
import shutil
import tarfile
import time

import billiard as multiprocessing
from celery import Celery
from celery.task import task
from common import data, helpers
from ConfigParser import ConfigParser
from model_execution_worker import calcBEutils

'''
Celery task wrapper for Oasis ktools calculation. 
'''

CONFIG_PARSER = ConfigParser()
CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
INI_PATH = os.path.abspath(os.path.join(CURRENT_DIRECTORY, 'Tasks.ini'))
CONFIG_PARSER.read(INI_PATH)

#LOG_FILENAME = CONFIG_PARSER.get('Default', 'LOG_FILENAME')
#LOG_LEVEL = CONFIG_PARSER.get('Default', 'LOG_LEVEL')
#NUMERIC_LOG_LEVEL = getattr(logging, LOG_LEVEL.upper(), None)

INPUTS_DATA_DIRECTORY = CONFIG_PARSER.get('Default', 'INPUTS_DATA_DIRECTORY')
OUTPUTS_DATA_DIRECTORY = CONFIG_PARSER.get('Default', 'OUTPUTS_DATA_DIRECTORY')
MODEL_DATA_DIRECTORY =  CONFIG_PARSER.get('Default', 'MODEL_DATA_DIRECTORY')
WORKING_DIRECTORY =  CONFIG_PARSER.get('Default', 'WORKING_DIRECTORY')
 
ARCHIVE_FILE_SUFFIX = '.tar'

#if not isinstance(NUMERIC_LOG_LEVEL, int):
#    raise ValueError('Invalid log level: %s' % LOG_LEVEL)

#logging.basicConfig(
#    filename=LOG_FILENAME,
#    level=NUMERIC_LOG_LEVEL,
#    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


CELERY = Celery()
CELERY.config_from_object('common.CeleryConfig')

@task(name='run_analysis', bind=True)
def start_analysis_task(self, input_location, analysis_settings_json):
    '''
    Task wrapper for running an analysis.
    Args:
        analysis_profile_json (string): The analysis settings.
    Returns:
        (string) The location of the outputs.   
    '''
    frame = inspect.currentframe()
    func_name = inspect.getframeinfo(frame)[2]
    logging.info("STARTED: {}".format(func_name))
    args, _, _, values = inspect.getargvalues(frame)
    for i in args:
        if i == 'self': continue
        logging.info("{}={}".format(i, values[i]))
    start = time.time()

    try:
        self.update_state(state=helpers.TASK_STATUS_RUNNING)
        output_location = start_analysis(
            analysis_settings_json[0], 
            input_location)
    except Exception as e:
        logging.exception("Model execution task failed.")   
        raise e

    end = time.time()
    logging.info("COMPLETED: {} in {}s".format(func_name, round(end - start,2)))
 
    return output_location

def start_analysis(analysis_settings, input_location):
    '''
    Run an analysis.
    Args:
        analysis_profile_json (string): The analysis settings.
    Returns:
        (string) The location of the outputs.   
    '''
    os.chdir(WORKING_DIRECTORY)

    # Set up the following directory structure:
    # - WORKING_DIRECTORY
    # |-Analysis working directory
    #   |-static  (soft-link to model files)
    #   |-input   (upload repository)
    #   |-output  (model results will be written into this folder then archived to the download directory)
    #   |-working (scratch directory for model execution)

    # Check that the input archive exists and is valid
    input_archive = os.path.join(INPUTS_DATA_DIRECTORY, input_location + ARCHIVE_FILE_SUFFIX) 
    if not os.path.exists(input_archive):
        raise Exception("Inputs location not found: {}".format(input_archive))
    if not tarfile.is_tarfile(input_archive):
        raise Exception("Inputs location not a tarfile: {}".format(input_archive))

    module_supplier_id = analysis_settings['analysis_settings']['module_supplier_id']
    model_version_id = analysis_settings['analysis_settings']['model_version_id']
    logging.info("Model supplier - version = {} {}".format(module_supplier_id, model_version_id))

    # Get the supplier module and call it
    if not os.path.exists(os.path.join( 
        os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))),  
        module_supplier_id)):
        raise Exception("Supplier module not found.")        

    model_data_path = os.path.join(MODEL_DATA_DIRECTORY, module_supplier_id, model_version_id) 
    if not os.path.exists(model_data_path):
        raise Exception("Model data not found.")        

    logging.info("Setting up analysis working directory")

    working_directory = os.path.join(WORKING_DIRECTORY, helpers.generate_unique_filename())
    os.mkdir(working_directory)
    os.mkdir(os.path.join(working_directory, "working"))
    output_directory = os.path.join(working_directory, "output") 
    os.mkdir(output_directory)

    with tarfile.open(input_archive) as input_tarfile:
        input_tarfile.extractall(path=(os.path.join(working_directory, 'input')))
    #! TODO: check that all the inputs are created
    if not os.path.exists(os.path.join(working_directory, 'input')):
        raise Exception("Input archive did not extract correctly")

    #! Uncomment for Linux
    #os.symlink(model_data_path, os.path.join(working_directory, "static")) 
    shutil.copytree(model_data_path, os.path.join(working_directory, "static")) 

    loadModule =  __import__("{}.{}".format(module_supplier_id, "supplierWSs"), globals(), locals(), ['calc' ], -1 )

    os.chdir(working_directory)
    logging.info("Working directory = {}".format(working_directory))

    loadModule.calc(analysis_settings['analysis_settings'])

    output_location = helpers.generate_unique_filename()
    output_filepath = os.path.join(
        OUTPUTS_DATA_DIRECTORY, output_location + ARCHIVE_FILE_SUFFIX) 
    with tarfile.open(output_filepath, "w:gz") as tar:
        tar.add(output_directory, arcname="output")

    os.chdir(WORKING_DIRECTORY)   
     
    logging.info("Output location = {}".format(output_location))

    return output_location