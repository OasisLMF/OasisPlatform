import io
import os
import inspect
import sys
import unittest
import shutil
import tarfile
import time
import re
import subprocess

from flask import json
from random import randint

TEST_DIRECTORY = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
TEST_DATA_DIRECTORY = os.path.abspath(os.path.join(TEST_DIRECTORY, 'data'))
LIB_PATH = os.path.abspath(os.path.join(TEST_DIRECTORY, '..', 'src'))
sys.path.append(LIB_PATH)

from server import app
from common import data

class Test_JSON2cmdTests(unittest.TestCase):
    ''' 
    JSON to cmd tests - check correct sequence of cmds is produced given a JSON file
    '''

    def clean_directories(self):
        for f in os.listdir('../src/utils'):
            if 'test_result_' in f and '.cmd' in f:
                os.remove(os.path.join('../src/utils', f))
          
          
    def setUp(self):
        INPUTS_DATA_DIRECTORY = os.path.join(TEST_DIRECTORY, 'JSON2cmd_data')
        app.INPUTS_DATA_DIRECTORY = INPUTS_DATA_DIRECTORY
        app.APP.config['TESTING'] = True
        self.app = app.APP.test_client()


    def test_run_JSONs(self):
        self.clean_directories()
        for f in os.listdir(app.INPUTS_DATA_DIRECTORY):
            spf = f.split('.')
            if len(spf) == 2:
                if spf[1] == 'json':
                    
                    p = subprocess.Popen('python model_runner.py -a {} -c test_result_{}.cmd'.format(os.path.join(app.INPUTS_DATA_DIRECTORY, f), spf[0]), shell=True, cwd='../src/utils')
                    p.wait()
                    with open(os.path.join(app.INPUTS_DATA_DIRECTORY, '{}.cmd'.format((spf[0]))), 'r') as ref:
                        ref_data = ref.read()
                    with open(os.path.join('../src/utils', 'test_result_{}.cmd'.format(spf[0])), 'r') as test:
                        test_data = test.read()
                    assert ref_data == test_data 
                   

if __name__ == '__main__':
    unittest.main()
