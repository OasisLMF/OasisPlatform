"""
Oasis API application endpoints.
"""

import os
import uuid
import inspect
import traceback
import time
from ConfigParser import ConfigParser
from flask import Flask, Response, request, jsonify

APP = Flask(__name__)

CONFIG_PARSER = ConfigParser()
CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
INI_PATH = os.path.abspath(os.path.join(CURRENT_DIRECTORY, 'OasisApi.ini'))
CONFIG_PARSER.read(INI_PATH)

EXPOSURE_DATA_DIRECTORY = CONFIG_PARSER.get('Default', 'EXPOSURE_DATA_DIRECTORY')
RESULTS_DATA_DIRECTORY = CONFIG_PARSER.get('Default', 'RESULTS_DATA_DIRECTORY')

DATA_FILE_SUFFIX = '.tar'
GZIP_FILE_SUFFIX = '.gz'

HTTP_RESPONSE_OK = 200
HTTP_RESPONSE_INTERNAL_ERROR = 400
HTTP_RESPONSE_RESOURCE_NOT_FOUND = 404

@APP.route('/exposure', defaults={'location': None}, methods=["get"])
@APP.route('/exposure/<location>', methods=["get"])
def get_exposure(location):
    
    try:
        exposures = list()
        if location == None:
            for filename in os.listdir(EXPOSURE_DATA_DIRECTORY):
                
                filepath = os.path.join(EXPOSURE_DATA_DIRECTORY, filename)
                
                if not filepath.endswith(DATA_FILE_SUFFIX):
                    continue
                if not os.path.isfile(filepath):
                    continue

                size_in_bytes = os.path.getsize(filepath)
                created_date = time.ctime(os.path.getctime(filepath))
                exposures.append(
                    {
                        "location": str.replace(filename, DATA_FILE_SUFFIX, ''),
                        "size": size_in_bytes,
                        "created_date": created_date
                    })
        
            response = jsonify({"exposures": exposures})
        else:
            filename = str(location) + DATA_FILE_SUFFIX;
            filepath = os.path.join(EXPOSURE_DATA_DIRECTORY, filename)

            if not os.path.exists(filepath):
                response = Response(status=HTTP_RESPONSE_RESOURCE_NOT_FOUND)
            else:
                size_in_bytes = os.path.getsize(filepath)
                created_date = time.ctime(os.path.getctime(filepath))
                exposures.append(
                    {
                        "location": str.replace(filename, DATA_FILE_SUFFIX, ''),
                        "size": size_in_bytes,
                        "created_date": created_date
                    })
                response = jsonify({"exposures": exposures})

    except:
        print "Error in post_lookup"
        print traceback.format_exc()
        response = Response(status=HTTP_RESPONSE_INTERNAL_ERROR)

    return response

@APP.route('/exposure', methods=["post"])
def post_exposure():
    try:
        content_type = ''
        if 'Content-Type' in request.headers:
            content_type = request.headers['Content-Type']

        is_gzipped = False

        if 'Content-Encoding' in request.headers:
            content_encoding = request.headers['Content-Encoding']
            is_gzipped = (content_encoding == 'gzip')

        file = request.files['file']
        filename = str(uuid.uuid4())
        filepath = os.path.join(EXPOSURE_DATA_DIRECTORY, filename)
        file.save(filepath)

        # If zipped, extract the tar file
        #if is_gzipped:

        # Check the content, and if invalid delete

        size_in_bytes = os.path.getsize(filepath)
        created_date = time.ctime(os.path.getctime(filepath))

        exposure = {
            "location": filename,
            "size": size_in_bytes,
            "created_date": created_date
        }  

        response = jsonify({'exposures': [exposure]})

    except:
        print "Error in post_lookup"
        print traceback.format_exc()
        response = Response(status=HTTP_RESPONSE_INTERNAL_ERROR)

    return response

@APP.route('/exposure', defaults={'location': None}, methods=["get"])
@APP.route('/exposure/<location>', methods=["get"])
def delete_exposure(location):
    try:
        if location == None:
            
            for filename in os.listdir(EXPOSURE_DATA_DIRECTORY):
                
                filepath = os.path.join(EXPOSURE_DATA_DIRECTORY, filename)
                
                if not filepath.endswith(DATA_FILE_SUFFIX):
                    continue
                if not os.path.isfile(filepath):
                    continue
                os.remove(filepath)
            response = Response(status=HTTP_RESPONSE_OK)
        
        else:
            
            filename = str(location) + DATA_FILE_SUFFIX;
            filepath = os.path.join(EXPOSURE_DATA_DIRECTORY, filename)

            if not os.path.exists(filepath):
                response = Response(status=HTTP_RESPONSE_RESOURCE_NOT_FOUND)
            else:
                os.remove(filepath)
                response = Response(status=HTTP_RESPONSE_OK)
        
    except:
        print "Error in post_lookup"
        print traceback.format_exc()
        response = Response(status=HTTP_RESPONSE_INTERNAL_ERROR)

    return response

@APP.route('/analysis', methods="post")
def post_analysis():
    return True
    
@APP.route('/analysis_queue', methods="get")
def get_analysis_queue():
    return True

@APP.route('/analysis_queue', methods="delete")
def delete_analysis_queue():
    return True

@APP.route('/results', methods="get")
def get_results():
    return True

@APP.route('/results', methods="delete")
def delete_results():
    return True
