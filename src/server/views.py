from datetime import timedelta
from flask import current_app, Blueprint
from flask import Response, request, jsonify
from flask_swagger import swagger
from flask.helpers import send_from_directory
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_refresh_token_required

from oasislmf.utils.log import oasis_log
from oasislmf.utils import http, status

from ..server.auth_backend import InvalidUserException
from ..conf.settings import settings
from ..common import data
from .celery import CELERY

import os
import logging
import time
import uuid

root = Blueprint('root', __name__)

TAR_FILE_SUFFIX = '.tar'
GZIP_FILE_SUFFIX = '.gz'


def _get_exposure_summary(filename):
    filepath = os.path.join(settings.get('server', 'INPUTS_DATA_DIRECTORY'), filename)
    if not filepath.endswith(TAR_FILE_SUFFIX):
        return None
    if not os.path.isfile(filepath):
        return None

    size_in_bytes = os.path.getsize(filepath)
    created_date = time.ctime(os.path.getctime(filepath))

    return data.ExposureSummary(
        location=filename.replace(TAR_FILE_SUFFIX, ''),
        size=size_in_bytes,
        created_date=created_date
    )


@root.route('/exposure_summary', defaults={'location': None}, methods=["GET"])
@root.route('/exposure_summary/<location>', methods=["GET"])
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
    logging.debug("Location: {}".format(location))
    if location is None:
        return jsonify({
            'exposures': [ex for ex in map(_get_exposure_summary, sorted(os.listdir(settings.get('server', 'INPUTS_DATA_DIRECTORY')))) if ex]
        })
    else:
        exposure = _get_exposure_summary('{}{}'.format(location, TAR_FILE_SUFFIX))
        if not exposure:
            return Response(status=http.HTTP_RESPONSE_RESOURCE_NOT_FOUND)

        return jsonify({'exposures': [exposure]})


@root.route('/exposure/<location>', methods=["GET"])
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
    logging.debug("Location: {}".format(location))
    return send_from_directory(settings.get('server', 'INPUTS_DATA_DIRECTORY'), location + TAR_FILE_SUFFIX)


@root.route('/exposure', methods=["POST"])
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
    request_file = request.files['file']
    filename = uuid.uuid4().hex
    filepath = os.path.join(settings.get('server', 'INPUTS_DATA_DIRECTORY'), filename) + TAR_FILE_SUFFIX
    request_file.save(filepath)

    # Check the content, and if invalid delete

    size_in_bytes = os.path.getsize(filepath)
    created_date = time.ctime(os.path.getctime(filepath))

    exposure = {
        "location": filename,
        "size": size_in_bytes,
        "created_date": created_date
    }

    return jsonify({'exposures': [exposure]})


@root.route('/exposure', defaults={'location': None}, methods=["DELETE"])
@root.route('/exposure/<location>', methods=["DELETE"])
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
    logging.debug("Location: {}".format(location))
    if location is None:
        for filename in os.listdir(settings.get('server', 'INPUTS_DATA_DIRECTORY')):
            filepath = os.path.join(settings.get('server', 'INPUTS_DATA_DIRECTORY'), filename)
            if not filepath.endswith(TAR_FILE_SUFFIX):
                continue
            if not os.path.isfile(filepath):
                continue
            os.remove(filepath)
        response = Response(status=http.HTTP_RESPONSE_OK)
    else:
        filename = str(location) + TAR_FILE_SUFFIX
        filepath = os.path.join(settings.get('server', 'INPUTS_DATA_DIRECTORY'), filename)

        if not os.path.exists(filepath):
            response = Response(status=http.HTTP_RESPONSE_RESOURCE_NOT_FOUND)
        else:
            os.remove(filepath)
            response = Response(status=http.HTTP_RESPONSE_OK)

    return response


@root.route('/analysis/<input_location>', methods=["POST"])
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
    analysis_settings = request.json or {}
    if not validate_analysis_settings(analysis_settings) or not _get_exposure_summary('{}.tar'.format(input_location)):
        return Response(status=http.HTTP_RESPONSE_BAD_REQUEST)
    else:
        module_supplier_id = analysis_settings['analysis_settings']['module_supplier_id']
        model_version_id = analysis_settings['analysis_settings']['model_version_id']

        logging.info("Model supplier - version = {} {}".format(module_supplier_id, model_version_id))
        result = CELERY.send_task(
            'run_analysis',
            (input_location, [analysis_settings]),
            queue='{}-{}'.format(module_supplier_id, model_version_id)
        )

        task_id = result.task_id
        return jsonify({'location': task_id})


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


@root.route('/analysis_status/<location>', methods=["GET"])
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
    analysis_status = _get_analysis_status(location)

    # If there is no location for a successful analysis, retry once
    # and then fail the analysis as something has gone wrong
    if (analysis_status.status == status.STATUS_SUCCESS and analysis_status.outputs_location is None):
        logging.info("Successful analysis has no location - retrying")
        time.sleep(5)

        analysis_status = _get_analysis_status(location)
        if (analysis_status.status == status.STATUS_SUCCESS and analysis_status.outputs_location is None):
            logging.info("Successful analysis still has no location - fail")
            analysis_status.status = status.STATUS_FAILURE

    response = jsonify(analysis_status)
    logging.debug("Response: {}".format(response.data))

    return response


@root.route('/analysis_status', methods=["DELETE"])
@root.route('/analysis_status/<location>', methods=["DELETE"])
@oasis_log()
def delete_analysis_status(location):  # pragma: no cover
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
    except Exception:
        logging.exception("Failed to delete analysis status")
        response = Response(status=http.HTTP_RESPONSE_INTERNAL_SERVER_ERROR)
    return response


@root.route('/outputs/<location>', methods=["GET"])
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
    logging.debug("Location: {}".format(location))
    return send_from_directory(settings.get('server', 'OUTPUTS_DATA_DIRECTORY'), location + TAR_FILE_SUFFIX)


@root.route('/outputs', defaults={'location': None}, methods=["DELETE"])
@root.route('/outputs/<location>', methods=["DELETE"])
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
    logging.debug("Location: {}".format(location))
    if location is None:

        for filename in os.listdir(settings.get('server', 'OUTPUTS_DATA_DIRECTORY')):

            filepath = os.path.join(settings.get('server', 'OUTPUTS_DATA_DIRECTORY'), filename)

            if not filepath.endswith(TAR_FILE_SUFFIX):
                continue
            if not os.path.isfile(filepath):
                continue
            os.remove(filepath)
        response = Response(status=http.HTTP_RESPONSE_OK)

    else:

        filename = str(location) + TAR_FILE_SUFFIX
        filepath = os.path.join(settings.get('server', 'OUTPUTS_DATA_DIRECTORY'), filename)

        if not os.path.exists(filepath):
            response = Response(status=http.HTTP_RESPONSE_RESOURCE_NOT_FOUND)
        else:
            os.remove(filepath)
            response = Response(status=http.HTTP_RESPONSE_OK)

    return response


@root.route("/spec")
@oasis_log()
def spec():
    """
    Create Swagger docs
    """
    swag = swagger(current_app())
    swag['info']['version'] = "0.1"
    swag['info']['title'] = "Oasis API"
    return jsonify(swag)


@root.route('/healthcheck', methods=['GET'])
@oasis_log()
def get_healthcheck():
    '''
    Basic healthcheck response.
    '''

    # TODO: check job management connections
    logging.info("get_healthcheck")
    return "OK"


@root.route('/refresh_token', methods=['POST'])
def refresh_token():
    try:
        user = current_app.auth_backend.authenticate(**request.json)
    except InvalidUserException:
        return jsonify({'message': 'Incorrect credentials'}), 401

    expires_delta = timedelta(seconds=3600)
    ident = current_app.auth_backend.get_jwt_identity(user)
    data = {
        'refresh_token': create_refresh_token(identity=ident),
        'access_token': create_access_token(identity=ident, expires_delta=expires_delta),
        'token_type': 'Bearer',
        'expires_in': expires_delta.seconds
    }
    return jsonify(data), 200


@root.route('/access_token', methods=['post'])
@jwt_refresh_token_required
def access_token():
    expires_delta = timedelta(seconds=3600)
    ident = get_jwt_identity()
    ret = {
        'access_token': create_access_token(identity=ident, expires_delta=expires_delta),
        'token_type': 'Bearer',
        'expires_in': expires_delta.seconds,
    }
    return jsonify(ret), 200


def validate_analysis_settings(analysis_settings):
    return (
        'analysis_settings' in analysis_settings and
        'module_supplier_id' in analysis_settings['analysis_settings'] and
        'model_version_id' in analysis_settings['analysis_settings']
    )
