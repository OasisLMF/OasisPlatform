import importlib
import logging
import uuid
from contextlib import contextmanager

import fasteners
import json
import os
import shutil
import tarfile

import sys
from oasislmf.model_execution.bin import prepare_model_run_directory, prepare_model_run_inputs
from oasislmf.model_execution import runner
from oasislmf.utils import status
from oasislmf.utils.exceptions import OasisException
from oasislmf.utils.log import oasis_log
from pathlib2 import Path

from celery import Celery
from celery.task import task

from ..utils.path import setcwd
from ..conf.settings import settings

'''
Celery task wrapper for Oasis ktools calculation.
'''

ARCHIVE_FILE_SUFFIX = '.tar'

CELERY = Celery()
CELERY.config_from_object('src.conf.celery')

logging.info("Started worker")
logging.info("INPUTS_DATA_DIRECTORY: {}".format(settings.get('worker', 'INPUTS_DATA_DIRECTORY')))
logging.info("OUTPUTS_DATA_DIRECTORY: {}".format(settings.get('worker', 'OUTPUTS_DATA_DIRECTORY')))
logging.info("MODEL_DATA_DIRECTORY: {}".format(settings.get('worker', 'MODEL_DATA_DIRECTORY')))
logging.info("WORKING_DIRECTORY: {}".format(settings.get('worker', 'WORKING_DIRECTORY')))
logging.info("KTOOLS_BATCH_COUNT: {}".format(settings.get('worker', 'KTOOLS_BATCH_COUNT')))


class MissingInputsException(OasisException):
    def __init__(self, input_archive):
        super(MissingInputsException, self).__init__('Inputs location not found: {}'.format(input_archive))


class InvalidInputsException(OasisException):
    def __init__(self, input_archive):
        super(InvalidInputsException, self).__init__('Inputs location not a tarfile: {}'.format(input_archive))


class MissingModelDataException(OasisException):
    def __init__(self, model_data_path):
        super(MissingModelDataException, self).__init__('Model data not found: {}'.format(model_data_path))


@contextmanager
def get_lock():
    lock = fasteners.InterProcessLock(settings.get('worker', 'LOCK_FILE'))
    gotten = lock.acquire(blocking=False, timeout=settings.getfloat('worker', 'LOCK_TIMEOUT_IN_SECS'))
    yield gotten

    if gotten:
        lock.release()


@task(name='run_analysis', bind=True)
def start_analysis_task(self, input_location, analysis_settings_json):
    '''
    Task wrapper for running an analysis.
    Args:
        analysis_profile_json (string): The analysis settings.
    Returns:
        (string) The location of the outputs.
    '''

    with get_lock() as gotten:
        if not gotten:
            logging.info("Failed to get resource lock - retry task")
            retry_countdown_in_secs = 10
            raise self.retry(countdown=retry_countdown_in_secs)

        logging.info("Acquired resource lock")

        try:
            logging.info("INPUTS_DATA_DIRECTORY: {}".format(settings.get('worker', 'INPUTS_DATA_DIRECTORY')))
            logging.info("OUTPUTS_DATA_DIRECTORY: {}".format(settings.get('worker', 'OUTPUTS_DATA_DIRECTORY')))
            logging.info("MODEL_DATA_DIRECTORY: {}".format(settings.get('worker', 'MODEL_DATA_DIRECTORY')))
            logging.info("WORKING_DIRECTORY: {}".format(settings.get('worker', 'WORKING_DIRECTORY')))
            logging.info("KTOOLS_BATCH_COUNT: {}".format(settings.get('worker', 'KTOOLS_BATCH_COUNT')))

            self.update_state(state=status.STATUS_RUNNING)
            output_location = start_analysis(analysis_settings_json[0], input_location)
        except Exception:
            logging.exception("Model execution task failed.")
            raise

        return output_location


@oasis_log()
def start_analysis(analysis_settings, input_location):
    '''
    Run an analysis.
    Args:
        analysis_profile_json (string): The analysis settings.
    Returns:
        (string) The location of the outputs.
    '''
    # Check that the input archive exists and is valid
    input_archive = os.path.join(
        settings.get('worker', 'INPUTS_DATA_DIRECTORY'),
        input_location + ARCHIVE_FILE_SUFFIX
    )

    if not os.path.exists(input_archive):
        raise MissingInputsException(input_archive)
    if not tarfile.is_tarfile(input_archive):
        raise InvalidInputsException(input_archive)

    source_tag = analysis_settings['analysis_settings']['source_tag']
    analysis_tag = analysis_settings['analysis_settings']['analysis_tag']
    logging.info(
        "Source tag = {}; Analysis tag: {}".format(analysis_tag, source_tag)
    )

    module_supplier_id = analysis_settings['analysis_settings']['module_supplier_id']
    model_version_id = analysis_settings['analysis_settings']['model_version_id']
    logging.info(
        "Model supplier - version = {} {}".format(module_supplier_id, model_version_id)
    )

    # Get the supplier module and call it
    use_default_model_runner = not Path(settings.get('worker', 'SUPPLIER_MODULE_DIRECTORY'), module_supplier_id).exists()

    model_data_path = os.path.join(
        settings.get('worker', 'MODEL_DATA_DIRECTORY'),
        module_supplier_id,
        model_version_id
    )

    if not os.path.exists(model_data_path):
        raise MissingModelDataException(model_data_path)

    logging.info("Setting up analysis working directory")

    directory_name = "{}_{}_{}".format(source_tag, analysis_tag, uuid.uuid4().hex)
    working_directory = os.path.join(settings.get('worker', 'WORKING_DIRECTORY'), directory_name)

    prepare_model_run_directory(working_directory, model_data_src_path=model_data_path, inputs_archive=input_archive)
    prepare_model_run_inputs(analysis_settings, working_directory)

    with setcwd(working_directory):
        logging.info("Working directory = {}".format(working_directory))

        # Persist the analysis_settings
        with open("analysis_settings.json", "w") as json_file:
            json.dump(analysis_settings, json_file)

        if use_default_model_runner:
            model_runner_module = runner
        else:
            sys.path.append(settings.get('worker', 'SUPPLIER_MODULE_DIRECTORY'))
            model_runner_module = importlib.import_module('{}.supplier_model_runner'.format(module_supplier_id))

        model_runner_module.run(
            analysis_settings['analysis_settings'], settings.getint('worker', 'KTOOLS_BATCH_COUNT'))

        output_location = uuid.uuid4().hex
        output_filepath = os.path.join(
            settings.get('worker', 'OUTPUTS_DATA_DIRECTORY'), output_location + ARCHIVE_FILE_SUFFIX)

        output_directory = os.path.join(working_directory, "output")
        with tarfile.open(output_filepath, "w:gz") as tar:
            tar.add(output_directory, arcname="output")

    if settings.getboolean('worker', 'DO_CLEAR_WORKING'):
        shutil.rmtree(working_directory, ignore_errors=True)

    logging.info("Output location = {}".format(output_location))

    return output_location
