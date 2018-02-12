"""
Oasis API server application endpoints.
"""
from __future__ import absolute_import

import json
import os
import logging
import time
import uuid

from celery import Celery
from oasislmf.utils import http, status
from oasislmf.utils.log import oasis_log

from ..common import data
from flask import Flask, Response, request, jsonify
from flask_swagger import swagger
from flask.helpers import send_from_directory

from .settings import settings

APP = Flask(__name__)

TAR_FILE_SUFFIX = '.tar'
GZIP_FILE_SUFFIX = '.gz'

CELERY = Celery()
CELERY.config_from_object('common.CeleryConfig')


@APP.route('/exposure_summary', defaults={'location': None}, methods=["GET"])
@APP.route('/exposure_summary/<location>', methods=["GET"])
@oasis_log()
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
    def _get_exposure_summary(filename):
        filepath = os.path.join(settings['INPUTS_DATA_DIRECTORY'], filename)
        if not filepath.endswith(TAR_FILE_SUFFIX):
            return None
        if not os.path.isfile(filepath):
            return None

        size_in_bytes = os.path.getsize(filepath)
        created_date = time.ctime(os.path.getctime(filepath))

        return data.ExposureSummary(
            location=str.replace(filename, TAR_FILE_SUFFIX, ''),
            size=size_in_bytes,
            created_date=created_date
        )

    try:
        logging.debug("Location: {}".format(location))
        if location is None:
            return jsonify({
                'exposures': [ex for ex in map(_get_exposure_summary, sorted(os.listdir(settings['INPUTS_DATA_DIRECTORY']))) if ex]
            })
        else:
            exposure = _get_exposure_summary('{}{}'.format(location, TAR_FILE_SUFFIX))
            if not exposure:
                return Response(status=http.HTTP_RESPONSE_RESOURCE_NOT_FOUND)

            return jsonify({'exposures': [exposure]})
    except:
        logging.exception("Failed to get exposure summary")
        return Response(status=http.HTTP_RESPONSE_INTERNAL_SERVER_ERROR)


@APP.route('/exposure/<location>', methods=["GET"])
@oasis_log()
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
            return Response(status=http.HTTP_RESPONSE_BAD_REQUEST)

        filename = str(location) + TAR_FILE_SUFFIX
        filepath = os.path.join(settings['INPUTS_DATA_DIRECTORY'], filename)
        if not os.path.exists(filepath):
            return Response(status=http.HTTP_RESPONSE_RESOURCE_NOT_FOUND)
        else:
            return send_from_directory(settings['INPUTS_DATA_DIRECTORY'], location + TAR_FILE_SUFFIX)
    except:
        logging.exception("Failed to get exposure")
        return Response(status=http.HTTP_RESPONSE_INTERNAL_SERVER_ERROR)


@APP.route('/exposure', methods=["POST"])
@oasis_log()
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
        filename = uuid.uuid4().hex
        filepath = os.path.join(settings['INPUTS_DATA_DIRECTORY'], filename) + TAR_FILE_SUFFIX
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
        response = Response(status=http.HTTP_RESPONSE_INTERNAL_SERVER_ERROR)

    return response


@APP.route('/exposure', defaults={'location': None}, methods=["DELETE"])
@APP.route('/exposure/<location>', methods=["DELETE"])
@oasis_log()
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
            for filename in os.listdir(settings['INPUTS_DATA_DIRECTORY']):
                filepath = os.path.join(settings['INPUTS_DATA_DIRECTORY'], filename)
                if not filepath.endswith(TAR_FILE_SUFFIX):
                    continue
                if not os.path.isfile(filepath):
                    continue
                os.remove(filepath)
            response = Response(status=http.HTTP_RESPONSE_OK)
        else:
            filename = str(location) + TAR_FILE_SUFFIX
            filepath = os.path.join(settings['INPUTS_DATA_DIRECTORY'], filename)

            if not os.path.exists(filepath):
                response = Response(status=http.HTTP_RESPONSE_RESOURCE_NOT_FOUND)
            else:
                os.remove(filepath)
                response = Response(status=http.HTTP_RESPONSE_OK)
    except:
        logging.exception("Failed to delete exposure")
        response = Response(status=http.HTTP_RESPONSE_INTERNAL_SERVER_ERROR)

    return response


@APP.route('/analysis/<input_location>', methods=["POST"])
@oasis_log()
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
            response = Response(status=http.HTTP_RESPONSE_BAD_REQUEST)
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
        response = Response(status=http.HTTP_RESPONSE_INTERNAL_SERVER_ERROR)
    return response


def _get_analysis_status(location):
    """
    Get the status of an analysis
    """
    result = CELERY.AsyncResult(location)
    logging.debug("celery result:{}".format(result.result))

    if result.state == status.STATUS_SUCCESS:
        analysis_status = data.AnalysisStatus(
            id=-1,
            status=status.STATUS_SUCCESS,
            message="",
            outputs_location=result.result)
    elif result.state == status.STATUS_FAILURE:
        analysis_status = data.AnalysisStatus(
            id=-1,
            status=status.STATUS_FAILURE,
            message=repr(result.result),
            outputs_location=None)
    else:
        analysis_status = data.AnalysisStatus(
            id=-1,
            status=result.state,
            message="",
            outputs_location=None)
    return analysis_status


@APP.route('/analysis_status/<location>', methods=["GET"])
@oasis_log()
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
                analysis_status.status == status.STATUS_SUCCESS and
                analysis_status.outputs_location is None):
            logging.info(
                "Successful analysis has no location - retrying")
            time.sleep(5)
            analysis_status = _get_analysis_status(location)
            if (
                    analysis_status.status == status.STATUS_SUCCESS and
                    analysis_status.outputs_location is None):
                logging.info(
                    "Successful analysis still has no location - fail")
                analysis_status.status = status.STATUS_FAILURE

        response = json.dumps(analysis_status.__dict__)
        logging.debug("Response: {}".format(response.data))
    except:
        logging.exception("Failed to get analysis status")
        response = Response(status=http.HTTP_RESPONSE_INTERNAL_SERVER_ERROR)
    return response


@APP.route('/analysis_status', methods=["DELETE"])
@APP.route('/analysis_status/<location>', methods=["DELETE"])
@oasis_log()
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
        response = Response(status=http.HTTP_RESPONSE_INTERNAL_SERVER_ERROR)
    return response


@APP.route('/outputs/<location>', methods=["GET"])
@oasis_log()
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
        file_path = os.path.join(settings['OUTPUTS_DATA_DIRECTORY'], location + TAR_FILE_SUFFIX)
        if not os.path.exists(file_path):
            response = Response(status=http.HTTP_RESPONSE_RESOURCE_NOT_FOUND)
        else:
            response = send_from_directory(settings['OUTPUTS_DATA_DIRECTORY'], location + TAR_FILE_SUFFIX)
    except:
        logging.exception("Failed to get outputs")
        response = Response(status=http.HTTP_RESPONSE_INTERNAL_SERVER_ERROR)
    return response


@APP.route('/outputs', methods=["DELETE"])
@APP.route('/outputs/<location>', methods=["DELETE"])
@oasis_log()
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

            for filename in os.listdir(settings['OUTPUTS_DATA_DIRECTORY']):

                filepath = os.path.join(settings['OUTPUTS_DATA_DIRECTORY'], filename)

                if not filepath.endswith(TAR_FILE_SUFFIX):
                    continue
                if not os.path.isfile(filepath):
                    continue
                os.remove(filepath)
            response = Response(status=http.HTTP_RESPONSE_OK)

        else:

            filename = str(location) + TAR_FILE_SUFFIX
            filepath = os.path.join(settings['OUTPUTS_DATA_DIRECTORY'], filename)

            if not os.path.exists(filepath):
                response = Response(status=http.HTTP_RESPONSE_RESOURCE_NOT_FOUND)
            else:
                os.remove(filepath)
                response = Response(status=http.HTTP_RESPONSE_OK)

    except:
        logging.exception("Failed to delete outputs")
        response = Response(status=http.HTTP_RESPONSE_INTERNAL_SERVER_ERROR)

    return response


@APP.route("/spec")
@oasis_log()
def spec():
    """
    Create Swagger docs
    """
    swag = swagger(APP)
    swag['info']['version'] = "0.1"
    swag['info']['title'] = "Oasis API"
    return jsonify(swag)


@APP.route('/healthcheck', methods=['GET'])
@oasis_log()
def get_healthcheck():
    '''
    Basic healthcheck response.
    '''

    #TODO: check job management connections
    logging.info("get_healthcheck")
    return "OK"


def validate_analysis_settings(analysis_settings_json):
    #TODO
    return True
