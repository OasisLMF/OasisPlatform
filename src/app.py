"""
Oasis API application endpoints.
"""

import os
import uuid
import inspect
import tarfile
import time
import traceback
from ConfigParser import ConfigParser
from flask import Flask, Response, request, jsonify
from flask_swagger import swagger
from celery import Celery

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

CELERY = Celery()
CELERY.config_from_object('CeleryConfig')

@APP.route('/exposure_summary', defaults={'location': None}, methods=["GET"])
@APP.route('/exposure_summary/<location>', methods=["GET"])
def get_exposure_summary(location):
    """
    Get exposure summary
    ---
    description: Gets a summary of a exposure resources and their contents. If location parameter is not supplied returns a summary of all exposures.
    produces:
    - application/json
    responses:
        '200':
            description: A list of exposure summaries.
            type: array
            items:
                $ref: '#/definitions/exposure_summary'
        '404':
            description: Resource not found
    parameters:
    - name: location
      in: path
      description: The location of the exposure resource to summarise.
      required: false
      type: str
    """
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

@APP.route('/exposure/<location>', methods=["GET"])
def get_exposure(location):
    """
    Get an exposure resource
    ---
    description: Returns an exposure resource. If location parameter is not supplied returns a summary of all exposures.
    produces:
    - application/json
    responses:
        '200':
            description: A compressed tar file containing the Oasis exposure files.
            type: file
        '404':
            description: Resource not found
    parameters:
    - name: location
      in: path
      description: The location of the exposure resource.
      required: true
      type: str
    """
    return True

@APP.route('/exposure', methods=["POST"])
def post_exposure():
    """
    Upload an exposure resource
    ---
    description: Uploads an exposure resourceby posting an exposure tar file. The tar file can be compressed or uncompressed.
    produces:
    - application/json
    responses:
        '200':
            description: The exposure summary of the created resource.
        schema:
          type: '#/definitions/expposure_summary'
    responses:
        '200':
            description: The exposure summary of the uploaded exposure resource.
            type: file 
        '404':
            description: Resource not found
    """
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
        filepath = os.path.join(EXPOSURE_DATA_DIRECTORY, filename) + DATA_FILE_SUFFIX
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

@APP.route('/exposure', defaults={'location': None}, methods=["DELETE"])
@APP.route('/exposure/<location>', methods=["DELETE"])
def delete_exposure(location):
    """
    Delete an exposure resource
    ---
    description: Deletes an exposure resource. If no location is given all exposure resources will be deleted.
    produces:
    - application/json
    responses:
        '200':
            description: OK
        '404':
            description: Resource not found
    parameters:
    - name: location
      in: path
      description: location of exposure resource to delete.
      required: true
      type: str
    """
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

@APP.route('/analysis', methods=["POST"])
def post_analysis():
    """
    Start an analysis
    ---
    description: Starts an analysis by creating an analysis queue resource.
    produces:
    - application/json
    responses:
        '200':
            description: The analysis_queue resource for the new analysis.
        schema:
          type: '#/definitions/analysis_queue'
    parameters:
    - name: file
      in: body
      description: The analysis settings 
      required: true
      type: file
    """
    result = CELERY.send_task("tasks.start_analysis", ["ANALYSIS_SETTINGS_JSON"])
    task_id = result.task_id
    return jsonify({'location': task_id})
    
@APP.route('/analysis_queue/<location>', methods=["GET"])
def get_analysis_queue(location):
    """
    Get an analysis queue resource
    ---
    description: Gets an analysis queue resource. If no location is given all exposure queue resources are returned. 
    produces:
    - application/json
    responses:
        '200':
            description: A list of analysis queue resources.
        schema:
            type: array
            items:
                $ref: '#/definitions/analysis_queue'
        '404':
            description: Resource not found
    parameters:
    - name: location
      in: path
      description: The location of the results resource to download.
      required: true
      type: str
    """

    result = CELERY.AsyncResult(location)
    status = result.status
    return jsonify({'status': status})

@APP.route('/analysis_queue', methods=["DELETE"])
def delete_analysis_queue():
    """
    Delete an analysis queue resource
    ---
    description: Deletes an analysis queue resource. If no location is given all analysis queue resources will be deleted.
    produces:
    - application/json
    responses:
        '200':
            description: OK
        '404':
            description: Resource not found
    parameters:
    - name: location
      in: path
      description: The location of the analysis queue resource to delete.
      required: true
      type: str
    """
    #TODO
    return True

@APP.route('/results/<location>', methods=["GET"])
def get_results(location):
    """
    Get a results resource
    ---
    description: Gets a results resource, returning a compressed results tar file.
    produces:
    - application/json
    responses:
        '200':
            description: A list of exposure summaries.
            type: file
        '404':
            description: Resource not found
    parameters:
    - name: location
      in: path
      description: The location of the results resource to download.
      required: true
      type: str
    """
    return True

@APP.route('/results', methods="delete")
@APP.route('/results/<location>', methods=["DELETE"])
def delete_results(location):
    """
    Delete a results resource
    ---
    description: Deletes a results resource. If no location is given all results resources will be deleted.
    produces:
    - application/json
    responses:
        '200':
            description: OK
        '404':
            description: Resource not found
    parameters:
    - name: location
      in: path
      description: The location of the results resource to delete.
      required: true
      type: str
    """
    return True

@APP.route("/spec")
def spec():
    swag = swagger(APP)
    swag['info']['version'] = "0.1"
    swag['info']['title'] = "Oasis API"
    return jsonify(swag)

@APP.route('/healthcheck', methods=['GET'])
def get_healthcheck():
    '''
    Basic healthcheck response.
    '''

    # TODO: check job management connections

    logging.info("get_healthcheck")
    return "OK"

def validate_exposure_tar(filepath):
    tar = tarfile.open(filepath)
    members = tar.getmembers()
    return (len(members) == 7) and \
        (sum(1 for member in members if member.name == 'items.bin') == 1) and \
        (sum(1 for member in members if member.name == 'coverages.bin') == 1) and \
        (sum(1 for member in members if member.name == 'summaryxref.bin') == 1) and \
        (sum(1 for member in members if member.name == 'fm_programme.bin') == 1) and \
        (sum(1 for member in members if member.name == 'fm_policytc.bin') == 1) and \
        (sum(1 for member in members if member.name == 'fm_profile.bin') == 1) and \
        (sum(1 for member in members if member.name == 'fm_summaryxref.bin') == 1)
