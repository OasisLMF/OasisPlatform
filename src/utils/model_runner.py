#! /usr/bin/python
from __future__ import absolute_import

import os
import sys
import json
import shutil
import logging
import argparse

from multiprocessing import cpu_count

from ..model_execution_worker.supplier_model_runner import run

if __name__ == '__main__':
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
        if not os.path.exists(analysis_settings_json):
            raise Exception('Analysis settings file does not exist:{}'.format(analysis_settings_json))

        if not os.path.exists(analysis_root_directory):
            raise Exception('Analysis root directory does not exist:{}'.format(analysis_root_directory))

        # Parse the analysis settings file
        with open(analysis_settings_json) as file:
            settings = json.load(file)
            analysis_settings = settings['analysis_settings']

        os.chdir(analysis_root_directory)
        run(analysis_settings, args.number_of_processes)
    except Exception as e:
        logging.exception("Model execution task failed.")
        os.chdir(original_directory)
        sys.exit(1)
