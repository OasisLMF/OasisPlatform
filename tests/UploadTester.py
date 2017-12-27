#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import inspect
import os
import shutil
import sys
import tarfile
import time
import unittest

from random import randint

import requests
import requests_toolbelt

from flask import json

from requests_toolbelt.multipart.encoder import MultipartEncoder
from requests_toolbelt import threaded

TEST_DIRECTORY = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
UPLOAD_DATA_DIRECTORY = os.path.abspath(os.path.join(TEST_DIRECTORY, 'testupload'))
LIB_PATH = os.path.abspath(os.path.join(TEST_DIRECTORY, '..', 'src'))
sys.path.append(LIB_PATH)

from server import app


class Test_UploadTests(unittest.TestCase):
    ''' 
    Upload API tests
    '''    

    def clean_directories(self):
        if os.path.exists(UPLOAD_DATA_DIRECTORY):
            shutil.rmtree(UPLOAD_DATA_DIRECTORY)
        os.makedirs(UPLOAD_DATA_DIRECTORY)

    def createtestfiles(self, path, size):
        '''
        Create file of size bytes filled with dummy data
        which is difficult to compress.
        '''
        #with open(path, 'a'):
        #    os.utime(path, None)  

        #1024*1024*1024 # 1 GByte
        #check if file alread exists as it takes ages to create
        if not os.path.exists(path):
            #Test file needs to be created.
            with open(path, 'wb') as outfile: # Open for binary output
                for x in xrange(size):
                    outfile.write(chr(randint(0,255))) # Write a random byte
            outfile.close()        
     
    def make_gztarfile(self,output_filename, source_dir):
        #check if file already exists as it takes ages to create
        if not os.path.exists(output_filename):
            with tarfile.open(output_filename, "w:gz") as tar:
                tar.add(source_dir, arcname=os.path.basename(source_dir))
        
    def make_bztarfile(self,output_filename, source_dir):
        #check if file already exists as it takes ages to create
        if not os.path.exists(output_filename):        
            with tarfile.open(output_filename, "w:bz2") as tar:
                tar.add(source_dir, arcname=os.path.basename(source_dir))  
                                          
    
    def setUp(self):
        app.APP.config['TESTING'] = True
        self.app = app.APP.test_client()
        
    def test_upload_test_1(self):

        #filename1 = 'test1.csv'
        #filename2 = 'test2.csv'
        #tarfile1 = 'test1.tar.gz'
        #tarfile2 = 'test1.tar.bz2'
        tarfile1 = 'testtar1.tar.gz'
        tarfile2 = 'testtar2.tar.bz2'
        
        #self.createtestfiles(os.path.join(UPLOAD_DATA_DIRECTORY, filename1),1024*1024*1024)
        #self.createtestfiles(os.path.join(UPLOAD_DATA_DIRECTORY, filename2),1024*1024*1024)        

        #self.make_gztarfile(os.path.join(UPLOAD_DATA_DIRECTORY, tarfile1),os.path.join(UPLOAD_DATA_DIRECTORY, 'test1.csv'))
        #self.make_gztarfile(os.path.join(UPLOAD_DATA_DIRECTORY, tarfile2),os.path.join(UPLOAD_DATA_DIRECTORY, 'test2.csv'))        

        upfile1 =  os.path.join(UPLOAD_DATA_DIRECTORY, tarfile1)
        upfile2 =  os.path.join(UPLOAD_DATA_DIRECTORY, tarfile2)

        m1 = MultipartEncoder(
            fields={'file': (tarfile1, open(upfile1, 'rb'), 'text/plain')})

        headers1={'Content-Type': m1.content_type}
        
        m2 = MultipartEncoder(
            fields={'file': (tarfile2, open(upfile2, 'rb'), 'text/plain')})

        headers2={'Content-Type': m2.content_type}
       

        urls_to_get = [{
             'url': 'http://127.0.0.1:5000/exposure',
             'method': 'POST',
             'data':m1,
             'headers':headers1
        }, {
             'url': 'http://127.0.0.1:5000/exposure',
             'method': 'POST',
             'data':m2,
             'headers':headers2             
        }]
        responses, errors = threaded.map(urls_to_get)
        
        for res in responses:
            print(res.response.content)
            assert res.response.status_code == 200
            
        for err in errors:
            print(err.exception.message)     
        
        
if __name__ == '__main__':
    unittest.main()        