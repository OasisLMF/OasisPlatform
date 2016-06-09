"""
Oasis API application endpoints.
"""

import os
import uuid
import inspect
import logging
import tarfile
import time
import traceback

from celery import Celery
from common import data
from common import helpers
from ConfigParser import ConfigParser
from flask import Flask, Response, request, jsonify
from flask_swagger import swagger
from flask.helpers import send_from_directory
from logging.handlers import RotatingFileHandler

APP = Flask(__name__)

CONFIG_PARSER = ConfigParser()
CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
INI_PATH = os.path.abspath(os.path.join(CURRENT_DIRECTORY, 'OasisApi.ini'))
CONFIG_PARSER.read(INI_PATH)
LOG_FILE = CONFIG_PARSER.get('Default', 'LOG_FILE')
LOG_LEVEL = CONFIG_PARSER.get('Default', 'LOG_LEVEL')
LOG_NUMERIC_LEVEL = getattr(logging, LOG_LEVEL.upper(), logging.DEBUG)
LOG_MAX_SIZE_IN_BYTES = CONFIG_PARSER.get('Default', 'LOG_MAX_SIZE_IN_BYTES')
LOG_BACKUP_COUNT = CONFIG_PARSER.get('Default', 'LOG_BACKUP_COUNT')

HANDLER = RotatingFileHandler(
    LOG_FILE, maxBytes=LOG_MAX_SIZE_IN_BYTES, backupCount=LOG_BACKUP_COUNT)
APP.logger.setLevel(logging.DEBUG)
APP.logger.addHandler(HANDLER)
FORMATTER = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
HANDLER.setFormatter(FORMATTER)

INPUTS_DATA_DIRECTORY = CONFIG_PARSER.get('Default', 'INPUTS_DATA_DIRECTORY')
OUTPUTS_DATA_DIRECTORY = CONFIG_PARSER.get('Default', 'OUTPUTS_DATA_DIRECTORY')

TAR_FILE_SUFFIX = '.tar'
GZIP_FILE_SUFFIX = '.gz'

CELERY = Celery()
CELERY.config_from_object('common.CeleryConfig')

@APP.route('/exposure_summary', defaults={'location': None}, methods=["GET"])
@APP.route('/exposure_summary/<location>', methods=["GET"])
@helpers.oasis_log(APP.logger)
def get_exposure_summary(location):
    """
    Get exposure summary
    ---
    definitions:
     schema:
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
        APP.logger.debug("Location: {}".format(location))
        if location is None:
            exposure_summaries = list()
            for filename in os.listdir(INPUTS_DATA_DIRECTORY):

                filepath = os.path.join(INPUTS_DATA_DIRECTORY, filename)
                
                if not filepath.endswith(TAR_FILE_SUFFIX):
                    continue
                if not os.path.isfile(filepath):
                    continue

                size_in_bytes = os.path.getsize(filepath)
                created_date = time.ctime(os.path.getctime(filepath))
                exposure_summaries.append(
                    ExposureSummary(
                        location=str.replace(filename, TAR_FILE_SUFFIX, ''),
                        size=size_in_bytes,
                        created_date=created_date))
            response = jsonify(
                {"exposures": [exposure_summary.__dict__ for exposure_summary in exposure_summaries]})
        else:
            filename = str(location) + TAR_FILE_SUFFIX
            filepath = os.path.join(INPUTS_DATA_DIRECTORY, filename)

            if not os.path.exists(filepath):
                response = Response(status=helpers.HTTP_RESPONSE_RESOURCE_NOT_FOUND)
            else:
                size_in_bytes = os.path.getsize(filepath)
                created_date = time.ctime(os.path.getctime(filepath))
                
                exposure_summary = ExposureSummary(
                    location=str.replace(filename, TAR_FILE_SUFFIX, ''),
                    size=size_in_bytes,
                    created_date=created_date)
                response = jsonify({"exposures": [exposure_summary.__dict__]})
                APP.logger.debug("Exposures: " + response.data)
    except:
        APP.log_exception(traceback.format_exc())
        response = Response(status=helpers.HTTP_RESPONSE_INTERNAL_ERROR)

    return response

@APP.route('/exposure/<location>', methods=["GET"])
@helpers.oasis_log(APP.logger)
def get_exposure(location):
    """
    Get an exposure resource
    ---
    description: Returns an exposure resource. If no location parameter is supplied 
       returns a summary of all exposures.
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
    # TODO
    try:
        True
    except:
        APP.log_exception(traceback.format_exc())
        response = Response(status=helpers.HTTP_RESPONSE_INTERNAL_ERROR)

    return response

@APP.route('/exposure', methods=["POST"])
@helpers.oasis_log(APP.logger)
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
        filename = helpers.generate_unique_filename()
        filepath = os.path.join(INPUTS_DATA_DIRECTORY, filename) + TAR_FILE_SUFFIX
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
        APP.log_exception(traceback.format_exc())
        response = Response(status=helpers.HTTP_RESPONSE_INTERNAL_ERROR)

    return response

@APP.route('/exposure', defaults={'location': None}, methods=["DELETE"])
@APP.route('/exposure/<location>', methods=["DELETE"])
@helpers.oasis_log(APP.logger)
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
        APP.logger.debug("Location: {}".format(location))
        if location is None:

            for filename in os.listdir(INPUTS_DATA_DIRECTORY):
                
                filepath = os.path.join(INPUTS_DATA_DIRECTORY, filename)
    
                if not filepath.endswith(TAR_FILE_SUFFIX):
                    continue
                if not os.path.isfile(filepath):
                    continue
                os.remove(filepath)
            response = Response(status=helpers.HTTP_RESPONSE_OK)
        
        else:
            
            filename = str(location) + TAR_FILE_SUFFIX;
            filepath = os.path.join(INPUTS_DATA_DIRECTORY, filename)

            if not os.path.exists(filepath):
                response = Response(status=helpers.HTTP_RESPONSE_RESOURCE_NOT_FOUND)
            else:
                os.remove(filepath)
                response = Response(status=helpers.HTTP_RESPONSE_OK)
    except:
        APP.log_exception(traceback.format_exc())
        response = Response(status_code.HTTP_RESPONSE_INTERNAL_ERROR) 

    return response

@APP.route('/analysis', methods=["POST"])
@helpers.oasis_log(APP.logger)
def post_analysis():
    """
    Start an analysis
    ---
    description: Starts an analysis by creating an analysis status resource.
    produces:
    - application/json
    responses:
        200:  
            description: The analysis status resource for the new analysis.
            schema:
                $ref: '#/definitions/AnalysisStatus'
    produces:
    - application/json
    parameters:
    - name: analysis_settings
      in: formData
      description: The analysis settings 
      required: true
      type: file
    """
    try:
        analysis_settings = request.json
        if not validate_analysis_settings(analysis_settings):
            response = Response(status_code = HTTP_RESPONSE_BAD_REQUEST)
        else:
            result = CELERY.send_task("tasks.start_analysis", [analysis_settings])
            task_id = result.task_id
            response = jsonify({'location': task_id})
    except:
        APP.log_exception(traceback.format_exc())
        response = Response(status=helpers.HTTP_RESPONSE_INTERNAL_ERROR)
    return response

@APP.route('/analysis_status/<location>', methods=["GET"])
@helpers.oasis_log(APP.logger)
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
            outputs_summary:
                type: OutputsSummary
                description: Summary of the outputs.
        id: OutputsSummary

        properties:
            location:
                type: string
                description: The location of the data.
            size:
                type: integer
                description: The size of the uncompressed data in bytes.
            created_date:
                type: string
                format: dateTime

                description: The date when the data was created.
    description: Gets an analysis status resource. If no location is given all exposure status resources are returned. 
    produces:
    - application/json
    responses:
        200:
            description: A list of analysis status resources.
            schema:
                type: array
                items:
                    $ref: '#/definitions/AnalysisStatus'
        404:
            description: Resource not found.
    parameters:
    -   name: location
        in: path
        description: The location of the outputs resource to download.
        required: true
        type: string
    """
    try:
        result = CELERY.AsyncResult(location)
        APP.logger.debug("celery result:{}".format(result.result))
       
        if result.state == helpers.TASK_STATUS_SUCCESS: 
            analysis_status = data.AnalysisStatus(
                id = -1,
                status = result.state,
                message="",             
                outputs_location=result.result)
        elif result.state == helpers.TASK_STATUS_FAILURE: 
            analysis_status = data.AnalysisStatus(
                id = -1,
                status = result.state,
                message=result.result,             
                outputs_location=None)
        else: 
            analysis_status = data.AnalysisStatus(
                id = -1,
                status = result.state,
                message="",             
                outputs_location=None)
         
        response = jsonify(analysis_status.__dict__)
        APP.logger.debug("Response: {}".format(response.data))
    except:
        APP.log_exception(traceback.format_exc())
        response = Response(status=helpers.HTTP_RESPONSE_INTERNAL_SERVER_ERROR)
    return response

@APP.route('/analysis_status', methods=["DELETE"])
@APP.route('/analysis_status/<location>', methods=["DELETE"])
@helpers.oasis_log(APP.logger)
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
    try:
        #TODO
        APP.logger.debug("Location: {}".format(location))
    except:
        APP.log_exception(traceback.format_exc())
        response = Response(status=helpers.HTTP_RESPONSE_INTERNAL_ERROR)
    return response

@APP.route('/outputs/<location>', methods=["GET"])
@helpers.oasis_log(APP.logger)
def get_outputs(location):
    """
    Get a outputs resource
    ---
    description: Gets a outputs resource, returning a compressed outputs tar file.
    produces:
    - application/json
    responses:
        200:
            description: A compressed tar of the outputs generated by an analysis.
        404:
            description: Resource not found.
    parameters:
    -   name: location
        in: path
        description: The location of the outputs resource to download.
        required: true
        type: string
    """
    try:
        APP.logger.debug("Location: {}".format(location))
        file_path = os.path.join(OUTPUTS_DATA_DIRECTORY, location + ".tar") 
        if not os.path.exists(file_path):
            response = Response(status_code = helpers.HTTP_RESPONSE_RESOURCE_NOT_FOUND)
        else:
            response = send_from_directory(OUTPUTS_DATA_DIRECTORY, location + ".tar")
    except:
        APP.log_exception(traceback.format_exc())
        response = Response(status=helpers.HTTP_RESPONSE_INTERNAL_ERROR)
    return response

@APP.route('/outputs', methods=["DELETE"])
@APP.route('/outputs/<location>', methods=["DELETE"])
@helpers.oasis_log(APP.logger)
def delete_outputs(location):
    """
    download_directory = '/var/www/oasis/download'
    Delete a outputs resource
    ---
    description: Deletes a outputs resource. If no location is given all outputs resources will be deleted.
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
      description: The location of the outputs resource to delete.
      required: true
      type: string
    """
    try:
        APP.logger.debug("Location: {}".format(location))
        if location is None:

            for filename in os.listdir(OUTPUTS_DATA_DIRECTORY):
                
                filepath = os.path.join(OUTPUTS_DATA_DIRECTORY, filename)
    
                if not filepath.endswith(TAR_FILE_SUFFIX):
                    continue
                if not os.path.isfile(filepath):
                    continue
                os.remove(filepath)
            response = Response(status=helpers.HTTP_RESPONSE_OK)
        
        else:
            
            filename = str(location) + TAR_FILE_SUFFIX;
            filepath = os.path.join(OUTPUTS_DATA_DIRECTORY, filename)

            if not os.path.exists(filepath):
                response = Response(status=helpers.HTTP_RESPONSE_RESOURCE_NOT_FOUND)
            else:
                os.remove(filepath)
                response = Response(status=helpers.HTTP_RESPONSE_OK)
        
    except:
        APP.logger.exception(traceback.format_exc())
        response = Response(status=helpers.HTTP_RESPONSE_INTERNAL_ERROR)

    return response

@APP.route("/spec")
@helpers.oasis_log(APP.logger)
def spec():
    swag = swagger(APP)
    swag['info']['version'] = "0.1"
    swag['info']['title'] = "Oasis API"
    return jsonify(swag)

@APP.route('/healthcheck', methods=['GET'])
@helpers.oasis_log(APP.logger)
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

def validate_analysis_settings(analysis_settings_json):
    # TODO
    return True
