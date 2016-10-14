#! /usr/bin/python

import os
import sys
import json
import inspect
import shutil
import logging
import argparse

from multiprocessing import cpu_count

CURRENT_DIRECTORY = \
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(CURRENT_DIRECTORY, ".."))
from model_execution import model_runner

parser = argparse.ArgumentParser(description='Run a model using ktools.')

parser.add_argument('-a', '--analysis_settings_json',
                    type=str,
                    required=True,
                    help="The analysis settings JSON file.")
parser.add_argument('-d', '--analysis_root_directory',
                    type=str,
                    default=os.getcwd(),
                    help="The analysis root directory.")
parser.add_argument('-p', '--number_of_processes',
                    type=int,
                    default=-1,
                    help="The number of processes to use. " +
                    "Defaults to the number of available cores.")
parser.add_argument('-v', '--verbose',
                    action='store_true',
                    help='Verbose logging.')

args = parser.parse_args()

analysis_settings_json = args.analysis_settings_json
analysis_root_directory = args.analysis_root_directory
number_of_processes = args.number_of_processes
do_verbose = args.verbose

if do_verbose:
    log_level = logging.DEBUG
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
else:
    log_level = logging.INFO
    log_format = ' %(message)s'

logging.basicConfig(stream=sys.stdout, level=log_level, format=log_format)

original_directory = os.getcwd()

try:
    # Set the number of processes
    if number_of_processes == -1:
        number_of_processes = cpu_count()

    if not os.path.exists(analysis_settings_json):
        raise Exception(
            'Analysis settings file does not exist:{}'
            .format(analysis_settings_json))

    if not os.path.exists(analysis_root_directory):
        raise Exception(
            'Analysis root directory does not exist:{}'
            .format(analysis_root_directory))

    # Parse the analysis settings file
    with open(analysis_settings_json) as file:
        json = json.load(file)
        analysis_settings = json['analysis_settings']

    os.chdir(analysis_root_directory)
    if os.path.exists("work"):
        shutil.rmtree('work')
    os.mkdir("work")
    if os.path.exists("fifo"):
        shutil.rmtree('fifo')
    os.mkdir("fifo")
    if os.path.exists("run_ktools.sh"):
        os.remove("run_ktools.sh")

    model_runner.run_analysis(analysis_settings, number_of_processes)  

except Exception as e:
    logging.exception("Model execution task failed.")
    os.chdir(original_directory)
    exit
