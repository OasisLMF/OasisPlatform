import io
import os
import inspect
import sys
import shutil
import uuid
import time
import shutil
import logging
import argparse

TEST_DIRECTORY = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
TEST_DATA_DIRECTORY = os.path.abspath(os.path.join(TEST_DIRECTORY, 'data'))
sys.path.append(os.path.join(TEST_DIRECTORY, '..', 'src'))

from common import helpers
from client import OasisApiClient

parser = argparse.ArgumentParser(description='Test the Oasis API client.')
parser.add_argument(
    '--url', metavar='N', type=str, default='http://localhost', required=False,
    help='The base URL for the API.')
parser.add_argument(
    '--num_analyses', metavar='N', type=int, default='1', required=False,
    help='The number of analyses to run.')

args = parser.parse_args()

base_url = args.url
num_analyses = args.num_analyses

sys.path.append(os.path.join(TEST_DIRECTORY, '..', 'src'))
inputs_data_directory = os.path.join(TEST_DIRECTORY, '..', 'example_data', 'inputs', 'nationwide')


upload_directory = os.path.join("upload", str(uuid.uuid1()))

shutil.copytree(
    os.path.join(inputs_data_directory, "csv"),
    upload_directory)

num_failed = 0
num_completed = 0

for analysis_id in range(num_analyses):
    try:
        logger = logging.Logger("Test", logging.DEBUG)
        logger.addHandler(logging.StreamHandler(sys.stdout))
        client = OasisApiClient.OasisApiClient(base_url, logger)
        inputs_location = client.upload_inputs_from_directory(upload_directory, do_validation=False)
        analysis_settings_json = "Test"
        #client.run_analysis(analysis_settings_json, inputs_location, "outputs", do_clean=False)
        client.run_analysis(analysis_settings_json, "inputs", "outputs", do_clean=False)
        num_completed = num_completed + 1
    except Exception as e:
        print e.__class__, e.__doc__, e.message
        num_failed = num_failed + 1

print "Done. Num completed={}; Num failed={}".format(num_completed, num_failed)
