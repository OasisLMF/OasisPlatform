import os
import inspect
import sys
import logging
import argparse

CURRENT_DIRECTORY = \
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(CURRENT_DIRECTORY, ".."))
from client import OasisApiClient

'''
Test utility for running an ara analysis using the Oasis API.
'''

parser = argparse.ArgumentParser(
    description='Converts ktools CSV files to binary.')
parser.add_argument(
    '-d', '--input_data_directory', type=str, required=True,
    help="The input data directory.")
parser.add_argument(
    '-n', '--no_il', action='store_true',
    help='Do not require insured loss, so no FM files.')
parser.add_argument(
    '-v', '--verbose', action='store_true',
    help='Verbose logging.')

args = parser.parse_args()

input_data_directory = args.input_data_directory
do_il = not args.no_il
do_verbose = args.verbose

if do_verbose:
    log_level = logging.DEBUG
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
else:
    log_level = logging.INFO
    log_format = ' %(message)s'

logging.basicConfig(stream=sys.stdout, level=log_level, format=log_format)

client = OasisApiClient.OasisApiClient(None, logging.getLogger())
client.check_inputs_directory(input_data_directory, do_il)
client.create_binary_files(input_data_directory, do_il)
