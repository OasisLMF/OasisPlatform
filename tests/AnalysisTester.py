import io
import os
import inspect
import sys
import unittest
from flask import json
import shutil

import tarfile
import time

TEST_DIRECTORY = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
TEST_DATA_DIRECTORY = os.path.abspath(os.path.join(TEST_DIRECTORY, 'data'))
sys.path.append(os.path.join(TEST_DIRECTORY, '..', 'src', 'server'))
sys.path.append(os.path.join(TEST_DIRECTORY, '..', 'src', 'common'))

import app
import TaskStatus
import common.resource_classes

app.DO_GZIP_RESPONSE = False
sys.path.append(os.path.join(TEST_DIRECTORY, '..', 'src'))
exposure_data_directory = os.path.join(TEST_DIRECTORY, 'exposure_data')
app.EXPOSURE_DATA_DIRECTORY = exposure_data_directory
app.APP.config['TESTING'] = True
app = app.APP.test_client()

response = app.post("/analysis")
data = response.data
location = json.loads(response.data.decode('utf-8'))['location']
status = TaskStatus.TASK_STATUS_PENDING

while True:
    url ="/analysis_status/" + str(location) 
    response = app.get("/analysis_status/" + str(location))
    status = str(json.loads(response.data.decode('utf-8'))['status'])
    if status == TaskStatus.TASK_STATUS_SUCCESS:
        break
    if status == TaskStatus.TASK_STATUS_FAILURE:
        break
    time.sleep(10)

print 'Task completed'