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
from collections import namedtuple

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

class ExposureSummary(object):
   def __init__(self):
       self.location = ""
       self.size = 0
       self.created_date = ""
   def __init__(self, location, size, created_date):
       self.location = location
       self.size = size
       self.created_date = created_date

class ResultsSummary(object):
   def __init__(self):
       self.location = ""
       self.size = 0
       self.created_date = ""
   def __init__(self, location, size, created_date):
       self.location = location
       self.size = size
       self.created_date = created_date

class AnalysisStatus(object):
   def __init__(self):
       self.id = -1
       self.status = ""
       self.message = ""
       selef.results_summary = None

   def __init__(self, id, status, message, results_summary):
       self.id = id
       self.status = status
       self.message = message
       selef.results_summary = results_summary

@APP.route('/exposure_summary', defaults={'location': None}, methods=["GET"])
@APP.route('/exposure_summary/<location>', methods=["GET"])
def get_exposure_summary(location):
    """
    Get exposure summary
    ---
    definitions:
    - schema:
        id: ExposureSummary
        properties:
            location:
                type: string
                description: The location of the exposure data.
            size:
                type: integer
                description: The size of the uncompressed exposure data in bytes.
            created_date:
                type: string
                format: dateTime
                description: The date when the exposure data was uploaded.
    description: Gets a summary of a exposure resources and their contents. If location parameter is not supplied returns a summary of all exposures.
    produces:
    - application/json
    responses:
        200:
            description: A list of exposure summaries.
            schema:
                type: array
                items:
                    $ref: "#/definitions/ExposureSummary"
        404:
            description: Resource not found
    parameters:
    - name: location
      in: path
      description: The location of the exposure resource to summarise.
      required: true
      type: string
    """
    try:
        if location == None:
            exposure_summaries = list()
            for filename in os.listdir(EXPOSURE_DATA_DIRECTORY):
                
                filepath = os.path.join(EXPOSURE_DATA_DIRECTORY, filename)
                
                if not filepath.endswith(DATA_FILE_SUFFIX):
                    continue
                if not os.path.isfile(filepath):
                    continue

                size_in_bytes = os.path.getsize(filepath)
                created_date = time.ctime(os.path.getctime(filepath))
                exposure_summaries.append(
                    ExposureSummary(
                        location = str.replace(filename, DATA_FILE_SUFFIX, ''),
                        size = size_in_bytes,
                        created_date = created_date))
            response = jsonify({"exposures": [exposure_summary.__dict__ for exposure_summary in exposure_summaries]})
        else:
            filename = str(location) + DATA_FILE_SUFFIX;
            filepath = os.path.join(EXPOSURE_DATA_DIRECTORY, filename)

            if not os.path.exists(filepath):
                response = Response(status=HTTP_RESPONSE_RESOURCE_NOT_FOUND)
            else:
                size_in_bytes = os.path.getsize(filepath)
                created_date = time.ctime(os.path.getctime(filepath))
                exposure_summary = ExposureSummary(
                        location = str.replace(filename, DATA_FILE_SUFFIX, ''),
                        size = size_in_bytes,
                        created_date = created_date)
                response = jsonify({"exposures": [exposure_summary.__dict__]})
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
    description: Returns an exposure resource. If no location parameter is supplied returns a summary of all exposures.
    produces:
    - application/json
    responses:
        200:
            description: A compressed tar file containing the Oasis exposure files.
        404:
            description: Resource not found
    parameters:
    - name: location
      in: path
      description: The location of the exposure resource.
      required: true
      type: string
    """
    return True

@APP.route('/exposure', methods=["POST"])
def post_exposure():
    """
    Upload an exposure resource
    ---
    description: Uploads an exposure resource by posting an exposure tar file. The tar file can be compressed or uncompressed.
    produces:
    - application/json
    responses:
        200:
            description: The exposure summary of the created exposure resource.
            schema:
                $ref: '#/definitions/ExposureSummary'
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
        200:
            description: OK
        404:
            description: Resource not found
    parameters:
    - name: location
      in: path
      description: location of exposure resource to delete.
      required: true
      type: string
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
        200:  
            description: The analysis_queue resource for the new analysis.
            schema:
                $ref: '#/definitions/AnalysisQueue'
    produces:
    - application/json
    parameters:
    - name: analysis_settings
      in: formData
      description: The analysis settings 
      required: true
      type: file
    """
    result = CELERY.send_task("tasks.start_analysis", ["ANALYSIS_SETTINGS_JSON"])
    task_id = result.task_id
    return jsonify({'location': task_id})
    
@APP.route('/analysis_status/<location>', methods=["GET"])
def get_analysis_status(location):
    """
    Get an analysis status resource
    ---
    definitions:
    - schema:
        id: AnalysisStatus
        properties:
            id:
                type: string
                description: The analysis ID.
            status:
                type: string
                description: The analysis status.
            message:
                type: string
                description: The analysis status message.
            results_summary_location:
                type: string
                description: The location of the analysis results.
    description: Gets an analysis status resource. If no location is given all exposure status resources are returned. 
    produces:
    - application/json
    responses:
        200:
            description: A list of analysis status resources.
            schema:
                type: array
                items:
                    $ref: '#/definitions/Analysisstatus'
        404:
            description: Resource not found.
    parameters:
    -   name: location
        in: path
        description: The location of the results resource to download.
        required: true
        type: string
    """
    result = CELERY.AsyncResult(location)
    status = result.status
    return jsonify({'status': status})

@APP.route('/analysis_status', methods=["DELETE"])
@APP.route('/analysis_status/<location>', methods=["DELETE"])
def delete_analysis_status(location):
    """
    Delete an analysis status resource
    ---
    description: Deletes an analysis status resource. If no location is given all analysis status resources will be deleted.
    produces:
    - application/json
    responses:
        200:
            description: OK
        404:
            description: Resource not found
    parameters:
    - name: location
      in: path
      description: The location of the analysis status resource to delete.
      required: true
      type: string
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
        200:
            description: A compressed tar of the results generated by an analysis.
        404:
            description: Resource not found.
    parameters:
    -   name: location
        in: path
        description: The location of the results resource to download.
        required: true
        type: string
    """
    return True

@APP.route('/results', methods=["DELETE"])
@APP.route('/results/<location>', methods=["DELETE"])
def delete_results(location):
    """
    Delete a results resource
    ---
    description: Deletes a results resource. If no location is given all results resources will be deleted.
    produces:
    - application/json
    responses:
        200:
            description: OK
        404:
            description: Resource not found
    parameters:
    - name: location
      in: path
      description: The location of the results resource to delete.
      required: true
      type: string
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
