import io
import os
import inspect
import sys
import unittest
from flask import json
import shutil
import requests
import requests_toolbelt
from requests_toolbelt.multipart.encoder import MultipartEncoder
from requests_toolbelt import threaded
import tarfile
import time
import shutil
import logging
import uuid

TEST_DIRECTORY = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
TEST_DATA_DIRECTORY = os.path.abspath(os.path.join(TEST_DIRECTORY, 'data'))
sys.path.append(os.path.join(TEST_DIRECTORY, '..', 'src'))

from common import helpers
from client import OasisApiClient

sys.path.append(os.path.join(TEST_DIRECTORY, '..', 'src'))
inputs_data_directory = os.path.join(TEST_DIRECTORY, '..', 'example_data', 'inputs', 'nationwide')

base_url = "http://192.168.99.100:8001"
num_analyses = 10

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

##
## Upload the test exposure set
##

#print "Uploading exposure"
#tar_file = 'inputs.tar.gz' 
#inputs_tar_to_upload =  os.path.join(inputs_data_directory, tar_file)
#inputs_multipart_data = MultipartEncoder( \
#    fields={'file': (tar_file, open(inputs_tar_to_upload, 'rb'), 'text/plain')})

#response = requests.post(
#    base_url + "/exposure",
#    data=inputs_multipart_data,
#    headers={'Content-Type': inputs_multipart_data.content_type})

#if response.status_code != 200:
#    print "POST /exposure failed: " + str(response.status_code)
#    quit() 

#exposure_location = response.json()['exposures'][0]['location'] 
#print "Uploaded exposure. Location: " + exposure_location

##
## Run an analysis
##

#print "Running analysis"

#analysis_setings_data_directory = os.path.join(TEST_DIRECTORY, '..', 'example_data', 'analysis_settings')
#analysis_settings_file = os.path.join(analysis_setings_data_directory, 'analysis_settings_1.json') 

#with open(analysis_settings_file) as json_file:
#    analysis_settings_json = json.load(json_file)

#response = requests.post(
#    base_url + "/analysis",
#    json = analysis_settings_json)

#if response.status_code != 200:
#    print "POST /analysis failed: " + str(response.status_code)
#    quit() 

#location = response.json()['location']
#status = helpers.TASK_STATUS_PENDING
#print "Analysis started"

#analysis_poll_interval = 5

#while True:
#    response = requests.get(base_url + "/analysis_status/" + str(location))
#    status = response.json()['status']
#    print "Analysis status: " + status
#    if status == helpers.TASK_STATUS_SUCCESS:
#        break
#    if status == helpers.TASK_STATUS_FAILURE:
#        break
#    time.sleep(analysis_poll_interval)

#outputs_location = response.json()['outputs_location']

#print "Analysis completed"

##
## Download the results
##
#print "Downloading outputs"

#response = requests.get(base_url + "/outputs/" + outputs_location)

#if response.status_code != 200:
#    print "GET /outputs failed: " + str(response.status_code)
#    quit() 


#print "Downloaded outputs"

##
## Clear the repositories
##
#print "Deleting exposure"

#response = requests.delete(base_url + "/exposure/" + exposure_location)

#if response.status_code != 200:
#    print "DELETE /exposure failed: " + str(response.status_code)
#    quit() 

#print "Deleted exposure"

#print "Deleting outputs"

#response = requests.delete(base_url + "/outputs/" + outputs_location)

#if response.status_code != 200:
#    print "DELETE /outputs failed: " + str(response.status_code)
#    quit() 

#print "Deleted outputs"