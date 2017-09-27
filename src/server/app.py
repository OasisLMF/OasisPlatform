"""
Oasis API server application endpoints.
"""

import os
import inspect
import logging
import tarfile
import time

from celery import Celery
from common import data
from flask import Flask, Response, request, jsonify
from flask_swagger import swagger
from flask.helpers import send_from_directory

from oasis_utils import (
    oasis_utils,
    oasis_log_utils,
    oasis_sys_utils,
)

APP = Flask(__name__)

CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

INI_PATH = os.path.abspath(os.path.join(CURRENT_DIRECTORY, 'OasisApi.ini'))

CONFIG_PARSER = oasis_sys_utils.load_ini_file(INI_PATH)
CONFIG_PARSER['LOG_FILE'] = CONFIG_PARSER['LOG_FILE'].replace('%LOG_DIRECTORY%', CONFIG_PARSER['LOG_DIRECTORY'])

oasis_log_utils.read_log_config(CONFIG_PARSER)

INPUTS_DATA_DIRECTORY = CONFIG_PARSER['INPUTS_DATA_DIRECTORY']
OUTPUTS_DATA_DIRECTORY = CONFIG_PARSER['OUTPUTS_DATA_DIRECTORY']

TAR_FILE_SUFFIX = '.tar'
GZIP_FILE_SUFFIX = '.gz'

CELERY = Celery()
CELERY.config_from_object('common.CeleryConfig')

@APP.route('/exposure_summary', defaults={'location': None}, methods=["GET"])
@APP.route('/exposure_summary/<location>', methods=["GET"])
@oasis_log_utils.oasis_log()
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
    description: Gets a summary of a exposure resources and their contents.
                 If location parameter is not supplied returns a summary of 
                 all exposures.
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

    oasis_log_utils.read_log_config(CONFIG_PARSER)

    try:
        logging.debug("Location: {}".format(location))
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
                    data.ExposureSummary(
                        location=str.replace(filename, TAR_FILE_SUFFIX, ''),
                        size=size_in_bytes,
                        created_date=created_date))
            response = jsonify(
                {"exposures": [exposure_summary.__dict__ for exposure_summary in exposure_summaries]})
        else:
            filename = str(location) + TAR_FILE_SUFFIX
            filepath = os.path.join(INPUTS_DATA_DIRECTORY, filename)
            if not os.path.exists(filepath):
                response = Response(status=oasis_utils.HTTP_RESPONSE_RESOURCE_NOT_FOUND)
            else:
                size_in_bytes = os.path.getsize(filepath)
                created_date = time.ctime(os.path.getctime(filepath))
                exposure_summary = data.ExposureSummary(
                    location=str.replace(filename, TAR_FILE_SUFFIX, ''),
                    size=size_in_bytes,
                    created_date=created_date)
                response = jsonify({"exposures": [exposure_summary.__dict__]})
                logging.debug("Exposures: " + response.data)
    except:
        logging.exception("Failed to get exposure summary")
        response = Response(status=oasis_utils.HTTP_RESPONSE_INTERNAL_SERVER_ERROR)

    return response

@APP.route('/exposure/<location>', methods=["GET"])
@oasis_log_utils.oasis_log()
def get_exposure(location):
    """
    Get an exposure resource
    ---
    description: Returns an exposure resource.
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
    try:
        logging.debug("Location: {}".format(location))
        if location is None:
            response = Response(status=oasis_utils.HTTP_RESPONSE_BAD_REQUEST)
        else:
            filename = str(location) + TAR_FILE_SUFFIX
            filepath = os.path.join(INPUTS_DATA_DIRECTORY, filename)
            if not os.path.exists(filepath):
                response = Response(
                    status=oasis_utils.HTTP_RESPONSE_RESOURCE_NOT_FOUND)
            else:
                response = send_from_directory(
                    INPUTS_DATA_DIRECTORY, location + TAR_FILE_SUFFIX)
    except:
        logging.exception("Failed to get exposure")
        response = Response(status=oasis_utils.HTTP_RESPONSE_INTERNAL_SERVER_ERROR)

    return response

@APP.route('/exposure', methods=["POST"])
@oasis_log_utils.oasis_log()
def post_exposure():
    """
    Upload an exposure resource
    ---
    description: Uploads an exposure resource by posting an exposure tar file.
                 The tar file can be compressed or uncompressed.
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

        # is_gzipped = False

        if 'Content-Encoding' in request.headers:
            content_encoding = request.headers['Content-Encoding']
            is_gzipped = (content_encoding == 'gzip')

        request_file = request.files['file']
        filename = oasis_utils.generate_unique_filename()
        filepath = os.path.join(INPUTS_DATA_DIRECTORY, filename) + TAR_FILE_SUFFIX
        request_file.save(filepath)

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
        logging.exception("Failed to post exposure")
        response = Response(status=oasis_utils.HTTP_RESPONSE_INTERNAL_SERVER_ERROR)

    return response

@APP.route('/exposure', defaults={'location': None}, methods=["DELETE"])
@APP.route('/exposure/<location>', methods=["DELETE"])
@oasis_log_utils.oasis_log()
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
        logging.debug("Location: {}".format(location))
        if location is None:
            for filename in os.listdir(INPUTS_DATA_DIRECTORY):
                filepath = os.path.join(INPUTS_DATA_DIRECTORY, filename)
                if not filepath.endswith(TAR_FILE_SUFFIX):
                    continue
                if not os.path.isfile(filepath):
                    continue
                os.remove(filepath)
            response = Response(status=oasis_utils.HTTP_RESPONSE_OK)
        else:
            filename = str(location) + TAR_FILE_SUFFIX
            filepath = os.path.join(INPUTS_DATA_DIRECTORY, filename)

            if not os.path.exists(filepath):
                response = Response(status=oasis_utils.HTTP_RESPONSE_RESOURCE_NOT_FOUND)
            else:
                os.remove(filepath)
                response = Response(status=oasis_utils.HTTP_RESPONSE_OK)
    except:
        logging.exception("Failed to delete exposure")
        response = Response(status=oasis_utils.HTTP_RESPONSE_INTERNAL_SERVER_ERROR)

    return response

@APP.route('/analysis/<input_location>', methods=["POST"])
@oasis_log_utils.oasis_log()
def post_analysis(input_location):
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
    -   name: input_location
        in: path
        description: The location of the input resource to analyse.
        required: true
        type: string
    - name: analysis_settings
      in: formData
      description: The analysis settings
      required: true
      type: file
    """
    try:
        analysis_settings = request.json
        if not validate_analysis_settings(analysis_settings):
            response = Response(status_code=oasis_utils.HTTP_RESPONSE_BAD_REQUEST)
        else:
            module_supplier_id = \
                analysis_settings['analysis_settings']['module_supplier_id']
            model_version_id = \
                analysis_settings['analysis_settings']['model_version_id']
            logging.info(
                "Model supplier - version = {} {}".format(
                    module_supplier_id, model_version_id))
            result = CELERY.send_task(
                "run_analysis",
                (input_location, [analysis_settings]),
                queue="{}-{}".format(module_supplier_id, model_version_id))
            task_id = result.task_id
            response = jsonify({'location': task_id})
    except:
        logging.exception("Failed to post analysis")
        response = Response(status=oasis_utils.HTTP_RESPONSE_INTERNAL_SERVER_ERROR)
    return response


def _get_analysis_status(location):
    """
    Get the status of an analysis
    """
    result = CELERY.AsyncResult(location)
    logging.debug("celery result:{}".format(result.result))

    if result.state == oasis_utils.STATUS_SUCCESS:
        analysis_status = data.AnalysisStatus(
            id=-1,
            status=oasis_utils.STATUS_SUCCESS,
            message="",
            outputs_location=result.result)
    elif result.state == oasis_utils.STATUS_FAILURE:
        analysis_status = data.AnalysisStatus(
            id=-1,
            status=oasis_utils.STATUS_FAILURE,
            message=oasis_utils.escape_string_for_json(repr(result.result)),
            outputs_location=None)
    else:
        analysis_status = data.AnalysisStatus(
            id=-1,
            status=result.state,
            message="",
            outputs_location=None)
    return analysis_status

@APP.route('/analysis_status/<location>', methods=["GET"])
@oasis_log_utils.oasis_log()
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
    description: Gets an analysis status resource. If no location is given
                 all exposure status resources are returned.
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
        analysis_status = _get_analysis_status(location)

        # If there is no location for a successful analysis, retry once
        # and then fail the analysis as something has gone wrong
        if (
                analysis_status.status == oasis_utils.STATUS_SUCCESS and
                analysis_status.outputs_location is None):
            logging.info(
                "Successful analysis has no location - retrying")
            time.sleep(5)
            analysis_status = _get_analysis_status(location)
            if (
                    analysis_status.status == oasis_utils.STATUS_SUCCESS and
                    analysis_status.outputs_location is None):
                logging.info(
                    "Successful analysis still has no location - fail")
                analysis_status.status = oasis_utils.STATUS_FAILURE

        response = jsonify(analysis_status.__dict__)
        logging.debug("Response: {}".format(response.data))
    except:
        logging.exception("Failed to get analysis status")
        response = Response(status=oasis_utils.HTTP_RESPONSE_INTERNAL_SERVER_ERROR)
    return response

@APP.route('/analysis_status', methods=["DELETE"])
@APP.route('/analysis_status/<location>', methods=["DELETE"])
@oasis_log_utils.oasis_log()
def delete_analysis_status(location):
    """
    Delete an analysis status resource
    ---
    description: Deletes an analysis status resource. If no location
                 is given all analysis status resources will be deleted.
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

    raise Exception("Not implemented")

    try:
        logging.debug("Location: {}".format(location))
    except:
        logging.exception("Failed to delete analysis status")
        response = Response(status=oasis_utils.HTTP_RESPONSE_INTERNAL_SERVER_ERROR)
    return response

@APP.route('/outputs/<location>', methods=["GET"])
@oasis_log_utils.oasis_log()
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
        logging.debug("Location: {}".format(location))
        file_path = os.path.join(OUTPUTS_DATA_DIRECTORY, location + ".tar")
        if not os.path.exists(file_path):
            response = Response(status_code = oasis_utils.HTTP_RESPONSE_RESOURCE_NOT_FOUND)
        else:
            response = send_from_directory(OUTPUTS_DATA_DIRECTORY, location + ".tar")
    except:
        logging.exception("Failed to get outputs")
        response = Response(status=oasis_utils.HTTP_RESPONSE_INTERNAL_SERVER_ERROR)
    return response

@APP.route('/outputs', methods=["DELETE"])
@APP.route('/outputs/<location>', methods=["DELETE"])
@oasis_log_utils.oasis_log()
def delete_outputs(location):
    """
    download_directory = '/var/www/oasis/download'
    Delete a outputs resource
    ---
    description: Deletes a outputs resource. If no location is given all
                 outputs resources will be deleted.
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
        logging.debug("Location: {}".format(location))
        if location is None:

            for filename in os.listdir(OUTPUTS_DATA_DIRECTORY):

                filepath = os.path.join(OUTPUTS_DATA_DIRECTORY, filename)

                if not filepath.endswith(TAR_FILE_SUFFIX):
                    continue
                if not os.path.isfile(filepath):
                    continue
                os.remove(filepath)
            response = Response(status=oasis_utils.HTTP_RESPONSE_OK)

        else:

            filename = str(location) + TAR_FILE_SUFFIX
            filepath = os.path.join(OUTPUTS_DATA_DIRECTORY, filename)

            if not os.path.exists(filepath):
                response = Response(status=oasis_utils.HTTP_RESPONSE_RESOURCE_NOT_FOUND)
            else:
                os.remove(filepath)
                response = Response(status=oasis_utils.HTTP_RESPONSE_OK)

    except:
        logging.exception("Failed to delete outputs")
        response = Response(status=oasis_utils.HTTP_RESPONSE_INTERNAL_SERVER_ERROR)

    return response

@APP.route("/spec")
@oasis_log_utils.oasis_log()
def spec():
    """
    Create Swagger docs
    """
    swag = swagger(APP)
    swag['info']['version'] = "0.1"
    swag['info']['title'] = "Oasis API"
    return jsonify(swag)

@APP.route('/healthcheck', methods=['GET'])
@oasis_log_utils.oasis_log()
def get_healthcheck():
    '''
    Basic healthcheck response.
    '''

    #TODO: check job management connections
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
    #TODO
    return True
