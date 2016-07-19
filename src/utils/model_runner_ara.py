#! /usr/bin/python

import os
import sys
import json
import logging
from multiprocessing import cpu_count
import certifi
import requests
import argparse
import inspect
import shutil

CURRENT_DIRECTORY = \
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(CURRENT_DIRECTORY, ".."))

from model_execution import model_runner_ara, ara_session_utils

'''
Funcitionaity for calling ARA apis to genererate Hurloss
event footprints and vulneravility matrices.

API 1a -

API 1b -

API 2 -

API 3 -

API 1c -


The following acronyms are used:
EA - exposure area perils
EF - event footprint
VM - vulnerability matrix
'''
parser = argparse.ArgumentParser(description='Run ARA Hurloss.')

parser.add_argument('-i', '--ara_server_ip',
                    type=str,
                    required=True,
                    help="The IP address of the ARA server.")
parser.add_argument('-u', '--upx_file',
                    type=str,
                    default = "",
                    help="The UPX file containing the exposure data.")
parser.add_argument('-a', '--analysis_settings_json',
                    type=str,
                    required=True,
                    help="The analysis settings JSON file.")
parser.add_argument('-d', '--analysis_root_directory',
                    type=str,
                    default=os.getcwd(),
                    help="The analysis root directory.")
parser.add_argument('-p', '--number_of_partitions',
                    type=int,
                    default=-1,
                    help="The number of processes to use. " +
                    "Defaults to the number of available cores.")
parser.add_argument('-n', '--number_of_ara_server_cores',
                    type=int,
                    default=12,
                    help="The number of ARA server cores. " +
                    "Defaults to 12.")
parser.add_argument('-c', '--command_debug_file',
                    type=str,
                    default='',
                    help="Debug file for the generated commands.")
parser.add_argument('-v', '--verbose',
                    action='store_true',
                    help='Verbose logging.')

args = parser.parse_args()

ara_server_ip = args.ara_server_ip
upx_file = args.upx_file
analysis_settings_json = args.analysis_settings_json
number_of_partitions = args.number_of_partitions
api3_ef_request_concurency = args.number_of_ara_server_cores
command_debug_file = args.command_debug_file
do_verbose = args.verbose
analysis_root_directory = args.analysis_root_directory

do_create_session = True
if upx_file == "":
    do_create_session = False

do_command_output = not command_debug_file == ''

script_root_directory = \
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))


def log_command(command):
    ''' Log a command '''
    pass


if do_verbose:
    log_level = logging.DEBUG
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
else:
    log_level = logging.INFO
    log_format = ' %(message)s'

logging.basicConfig(stream=sys.stdout, level=log_level, format=log_format)

original_directory = os.getcwd()

try:

    logging.info("Do create session: {}".format(do_create_session))

    # Set the number of partitions
    if number_of_partitions == -1:
        number_of_partitions = cpu_count()
    if not os.path.exists(analysis_settings_json):
        raise Exception(
            'Analysis settings file does not exist:{}'
            .format(analysis_settings_json))

    if not os.path.exists(analysis_root_directory):
        raise Exception(
            'Analysis root directory does not exist:{}'
            .format(analysis_root_directory))
    analysis_root_directory = os.path.abspath(analysis_root_directory)

    if command_debug_file:
        fully_qualified_command_debug_file = \
            os.path.abspath(command_debug_file)
        with open(fully_qualified_command_debug_file, "w") as file:
            file.writelines("#!/bin/sh" + os.linesep)

        def log_command(command):
            with open(fully_qualified_command_debug_file, "a") as file:
                file.writelines(command + os.linesep)

    # Parse the analysis settings file
    with open(analysis_settings_json) as file:
        analysis_settings = json.load(file)['analysis_settings']

    data_directory = os.path.join(analysis_root_directory, "data")
    working_directory = os.path.join(analysis_root_directory, "working")

    if os.path.exists(working_directory):
        shutil.rmtree(working_directory)
    os.mkdir(working_directory)

    if os.path.exists(data_directory):
        shutil.rmtree(data_directory)
    os.mkdir(data_directory)

    url = 'https://{0}/oasis/'.format(ara_server_ip)
    upx_file = upx_file

    verify_string = False
    verify_mode = ""
    if verify_mode == "certifi":
        verify_string = certifi.where()

    if not verify_string:
        requests.packages.urllib3.disable_warnings()

    model_settings = analysis_settings["model_settings"]
    session_id = model_settings["session_id"]
    do_wind = bool(model_settings["peril_wind"])
    do_stormsurge = bool(model_settings["peril_surge"])
    do_demand_surge = bool(model_settings["demand_surge"])
    leakage_factor = float(model_settings["leakage_factor"])
    event_set_type = model_settings["event_set"]

    logging.info("Session ID: {}".format(session_id))
    logging.info("Do wind: {}".format(do_wind))    
    logging.info("Do surge: {}".format(do_stormsurge))
    
    if do_create_session:
        session_id = ara_session_utils.create_session(
                        url, upx_file, verify_string, do_stormsurge, data_directory)
        analysis_settings['session_id'] = session_id

    ea_wind_filename = os.path.join(
        data_directory, 'EA_Wind_Chunk_1.csv')
    ea_surge_filename = os.path.join(
        data_directory, 'EA_StormSurge_Chunk_1.csv')

    model_runner_ara.do_api2(url, session_id, event_set_type, do_stormsurge,
            ea_wind_filename, ea_surge_filename, verify_string)

    model_runner_ara.do_api3_vm(url, session_id, event_set_type, do_stormsurge,
               data_directory, "testVM.tar.gz", verify_string)

    model_runner_ara.do_api3_ef(number_of_partitions, api3_ef_request_concurency,
                                session_id, event_set_type, url, data_directory,
                                verify_string, model_runner_ara.PERIL_WIND)

    if do_stormsurge:
        model_runner_ara.do_api3_ef(number_of_partitions, api3_ef_request_concurency,
                                    session_id, event_set_type, url, data_directory,
                                    verify_string, model_runner_ara.PERIL_STORMSURGE)

    if do_create_session:
        model_runner_ara.do_api1c(url, session_id, verify_string)

    if do_create_session:
        shutil.copyfile(
            os.path.join(analysis_root_directory, "data", "coverages.bin"),
            os.path.join(analysis_root_directory, "input", "coverages.bin"))

        shutil.copyfile(
            os.path.join(analysis_root_directory, "data", "items.bin"),
            os.path.join(analysis_root_directory, "input", "items.bin"))
    else:
        shutil.copyfile(
            os.path.join(analysis_root_directory, "input", "coverages.bin"),
            os.path.join(analysis_root_directory, "data", "coverages.bin"))

        shutil.copyfile(
            os.path.join(analysis_root_directory, "input", "items.bin"),
            os.path.join(analysis_root_directory, "data", "items.bin"))

    os.chdir(analysis_root_directory)
    model_runner_ara.run_analysis_only(
        analysis_settings, number_of_partitions, log_command)
    os.chdir(original_directory)

except Exception as e:
    logging.exception("Model execution task failed.")
    os.chdir(original_directory)
    exit
