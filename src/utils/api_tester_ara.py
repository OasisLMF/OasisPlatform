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

CURRENT_DIRECTORY = \
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(CURRENT_DIRECTORY, ".."))

from common import helpers
from client import OasisApiClient
from model_execution import ara_session_utils

parser = argparse.ArgumentParser(description='Test the Oasis API client.')
parser.add_argument(
    '-i', '--api_ip', metavar='N', type=str, required=True,
    help='The oasis API IP address.')
parser.add_argument(
    '-s', '--ara_ip', metavar='N', type=str, required=True,
    help='The ARA server IP address.')
parser.add_argument(
    '-a', '--analysis_settings_json', type=str, default='', 
    help="The analysis settings JSON file.")
parser.add_argument(
    '-u', '--upx_file', type=str, required=True,
    help="The UPX file containing the exposure data.")
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
ara_ip = args.ara_ip
upx_file = args.upx_file
analysis_settings_json_filepath = args.analysis_settings_json
num_analyses = args.num_analyses
input_data_directory = args.input_data_directory
output_data_directory = args.output_data_directory
do_verbose = args.verbose

api_url = 'http://{0}'.format(api_ip)
ara_url = 'https://{0}/oasis/'.format(ara_ip)

if not os.path.exists(input_data_directory):
    print "Input data directory does not exist: {}".format(analysis_settings_json_filepath)
    exit()

if analysis_settings_json_filepath == "":
    analysis_settings_json_filepath = os.path.join(TEST_DATA_DIRECTORY, "analysis_settings.json")
if not os.path.exists(analysis_settings_json_filepath):
    print "Analysis settings file does not exist: {}".format(analysis_settings_json_filepath)
    exit()

if not os.path.exists(output_data_directory):
    os.makedirs(output_data_directory)

upload_directory = os.path.join("upload", str(uuid.uuid1()))

shutil.copytree(
    os.path.join(input_data_directory, "csv"),
    upload_directory)

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

model_settings = analysis_settings['analysis_settings']['model_settings']
do_stormsurge = bool(model_settings["peril_surge"])

for analysis_id in range(num_analyses):
    try:
        # Each analysis needs it's own session.
        verify_string = False
        session_id = ara_session_utils.create_session(
                        ara_url, upx_file, verify_string, do_stormsurge, 
                        upload_directory, file_type="csv")    
        analysis_settings['analysis_settings']['model_settings']['session_id'] = session_id
        client = OasisApiClient.OasisApiClient(api_url, logging.getLogger())
        input_location = client.upload_inputs_from_directory(upload_directory, do_validation=False)
        client.run_analysis(analysis_settings, input_location, output_data_directory, do_clean=False)
        num_completed = num_completed + 1
    except Exception as e:
        logging.exception("API test failed")
        num_failed = num_failed + 1

print "Done. Num completed={}; Num failed={}".format(num_completed, num_failed)
