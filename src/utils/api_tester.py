# Python 2 standard library imports
import argparse
import inspect
import json
import logging
import os
import shutil
import sys
import threading
import uuid

CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(CURRENT_DIRECTORY, ".."))

# Oasis Api import
from client import OasisApiClient

'''
Test utility for running an ara analysis using the Oasis API.
'''

parser = argparse.ArgumentParser(description='Test the Oasis API client.')
parser.add_argument(
    '-i', '--api_ip', metavar='N', type=str, required=True,
    help='The oasis API IP address.')
parser.add_argument(
    '-a', '--analysis_settings_json', type=str, required=True,
    help="The analysis settings JSON file.")
parser.add_argument(
    '-d', '--input_data_directory', type=str, required=True,
    help="The input data directory.")
parser.add_argument(
    '-o', '--output_data_directory', type=str, required=True,
    help="The output data directory.")
parser.add_argument(
    '-n', '--num_analyses', metavar='N', type=int, default='1',
    help='The number of analyses to run.')
parser.add_argument(
    '-v', '--verbose', action='store_true',
    help='Verbose logging.')

args = parser.parse_args()

api_ip = args.api_ip
analysis_settings_json_filepath = args.analysis_settings_json
num_analyses = args.num_analyses
input_data_directory = args.input_data_directory
output_data_directory = args.output_data_directory
do_verbose = args.verbose

api_url = 'http://{0}'.format(api_ip)

if not os.path.exists(input_data_directory):
    print "Input data directory does not exist: {}".format(
        analysis_settings_json_filepath)
    exit()

if not os.path.exists(analysis_settings_json_filepath):
    print "Analysis settings file does not exist: {}".format(
        analysis_settings_json_filepath)
    exit()

if not os.path.exists(output_data_directory):
    os.makedirs(output_data_directory)

num_failed = 0
num_completed = 0

if do_verbose:
    log_level = logging.DEBUG
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
else:
    log_level = logging.INFO
    log_format = ' %(message)s'

logging.basicConfig(stream=sys.stdout, level=log_level, format=log_format)

# Parse the analysis settings file
with open(analysis_settings_json_filepath) as file:
    analysis_settings = json.load(file)

do_il = bool(analysis_settings['analysis_settings']["il_output"])


class Counter:

    def __init__(self):
        self.num_failed = 0
        self.num_completed = 0

    def increment_num_completed(self):
        self.num_completed = self.num_completed + 1

    def increment_num_failed(self):
        self.num_failed = self.num_failed + 1


def run_analysis(c):
    try:

        upload_directory = os.path.join("upload", str(uuid.uuid1()))

        shutil.copytree(
            os.path.join(input_data_directory, "csv"),
            upload_directory)

        client = OasisApiClient.OasisApiClient(api_url, logging.getLogger())
        input_location = client.upload_inputs_from_directory(
            upload_directory, do_il, do_validation=False)
        client.run_analysis(
            analysis_settings, input_location,
            output_data_directory, do_clean=False)
        c.increment_num_completed()

    except Exception as e:
        logging.exception("API test failed")
        c.increment_num_failed()

analysis_threads = list()
c = Counter()
for analysis_id in range(num_analyses):
    analysis_threads.append(
        threading.Thread(target=run_analysis, args=[c])
    )

for t in analysis_threads:
    t.start()
for t in analysis_threads:
    t.join()

print "Done. Num completed={}; Num failed={}".format(
    c.num_completed, c.num_failed)
