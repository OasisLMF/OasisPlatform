import io
import json
import os
import inspect
import sys
import shutil
import uuid
import time
import shutil
import logging
import argparse
import traceback

TEST_DIRECTORY = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
TEST_DATA_DIRECTORY = os.path.abspath(os.path.join(TEST_DIRECTORY, 'data'))
sys.path.append(os.path.join(TEST_DIRECTORY, '..', 'src'))

from common import helpers
from client import OasisApiClient

parser = argparse.ArgumentParser(description='Test the Oasis API client.')
parser.add_argument(
    '-u', '--url', metavar='N', type=str, default='http://localhost:8001', required=False,
    help='The base URL for the API.')
parser.add_argument(
    '-n', '--num_analyses', metavar='N', type=int, default='1', required=False,
    help='The number of analyses to run.')

args = parser.parse_args()

base_url = args.url
num_analyses = args.num_analyses

sys.path.append(os.path.join(TEST_DIRECTORY, '..', 'src'))
#input_data_directory = os.path.join(TEST_DIRECTORY, '..', 'example_data', 'inputs', 'nationwide')
input_data_directory = TEST_DATA_DIRECTORY

output_data_directory = os.path.join(TEST_DIRECTORY, 'outputs')
if not os.path.exists(output_data_directory):
    os.makedirs(output_data_directory)

analysis_settings_data_directory = os.path.join(TEST_DIRECTORY, '..', 'example_data', 'analysis_settings_csv')
upload_directory = os.path.join("upload", str(uuid.uuid1()))

shutil.copytree(
    os.path.join(input_data_directory, "input", "csv"),
    upload_directory)

num_failed = 0
num_completed = 0

logger = logging.Logger("Test", logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

for analysis_id in range(num_analyses):
    try:
        client = OasisApiClient.OasisApiClient(base_url, logger)
        input_location = client.upload_inputs_from_directory(upload_directory, do_validation=False)
        with open(os.path.join(TEST_DATA_DIRECTORY, "analysis_settings.json")) as json_file:
            analysis_settings_json = json.load(json_file)

        client.run_analysis(analysis_settings_json, input_location, output_data_directory, do_clean=False)
        num_completed = num_completed + 1
    except Exception as e:
        logger.exception("API test failed")
        num_failed = num_failed + 1

print "Done. Num completed={}; Num failed={}".format(num_completed, num_failed)
