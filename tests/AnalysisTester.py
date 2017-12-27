#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import io
import inspect
import os
import shutil
import sys
import tarfile
import time
import unittest

from flask import json

import requests

TEST_DIRECTORY = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
TEST_DATA_DIRECTORY = os.path.abspath(os.path.join(TEST_DIRECTORY, 'data'))
sys.path.append(os.path.join(TEST_DIRECTORY, '..', 'src'))

#from server import app
from common import helpers

if __name__ == '__main__':

    #app.DO_GZIP_RESPONSE = False
    #sys.path.append(os.path.join(TEST_DIRECTORY, '..', 'src'))
    #INPUTS_DATA_DIRECTORY = os.path.join(TEST_DIRECTORY, 'exposure_data')
    #app.INPUTS_DATA_DIRECTORY = INPUTS_DATA_DIRECTORY
    #app.APP.config['TESTING'] = True
    #app = app.APP.test_client()

    response = app.post("/analysis")
    data = response.data
    location = json.loads(response.data.decode('utf-8'))['location']
    status = helpers.TASK_STATUS_PENDING

    while True:
        url ="/analysis_status/" + str(location) 
        response = app.get("/analysis_status/" + str(location))
        status = str(json.loads(response.data.decode('utf-8'))['status'])
        if status == helpers.TASK_STATUS_SUCCESS:
            break
        if status == helpers.TASK_STATUS_FAILURE:
            break
        time.sleep(10)

    print('Task completed. Task status: {}'.format(status))