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
from ConfigParser import ConfigParser
from flask import Flask, Response, request, jsonify
from flask_swagger import swagger
from celery import Celery
from common import data
from common import helpers

APP = Flask(__name__)

CONFIG_PARSER = ConfigParser()
CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
INI_PATH = os.path.abspath(os.path.join(CURRENT_DIRECTORY, 'OasisApi.ini'))
CONFIG_PARSER.read(INI_PATH)

EXPOSURE_DATA_DIRECTORY = CONFIG_PARSER.get('Default', 'EXPOSURE_DATA_DIRECTORY')
RESULTS_DATA_DIRECTORY = CONFIG_PARSER.get('Default', 'RESULTS_DATA_DIRECTORY')
UPLOAD_DATA_DIRECTORY = CONFIG_PARSER.get('Default', 'UPLOAD_DIRECTORY')

DATA_FILE_SUFFIX = '.tar'
GZIP_FILE_SUFFIX = '.gz'
ALLOWED_EXTENSIONS = set(['tar','gz','tar.gz','bz2','tar.bz2'])

HTTP_RESPONSE_OK = 200
HTTP_RESPONSE_INTERNAL_ERROR = 400
HTTP_RESPONSE_RESOURCE_NOT_FOUND = 404

CELERY = Celery()
CELERY.config_from_object('common.CeleryConfig')

@APP.route('/exposure_summary', defaults={'location': None}, methods=["GET"])
@APP.route('/exposure_summary/<location>', methods=["GET"])
@helpers.oasis_log
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
        if location is None:
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
                        location=str.replace(filename, DATA_FILE_SUFFIX, ''),
                        size=size_in_bytes,
                        created_date=created_date))
            response = jsonify(
                {"exposures": [exposure_summary.__dict__ for exposure_summary in exposure_summaries]})
        else:
            filename = str(location) + DATA_FILE_SUFFIX
            filepath = os.path.join(EXPOSURE_DATA_DIRECTORY, filename)

            if not os.path.exists(filepath):
                response = Response(status=HTTP_RESPONSE_RESOURCE_NOT_FOUND)
            else:
                size_in_bytes = os.path.getsize(filepath)
                created_date = time.ctime(os.path.getctime(filepath))
                
                exposure_summary = ExposureSummary(
                    location=str.replace(filename, DATA_FILE_SUFFIX, ''),
                    size=size_in_bytes,
                    created_date=created_date)
                response = jsonify({"exposures": [exposure_summary.__dict__]})
    except:
        print "Error in post_lookup"
        print traceback.format_exc()
        response = Response(status=HTTP_RESPONSE_INTERNAL_ERROR)

    return response

@APP.route('/exposure/<location>', methods=["GET"])
@helpers.oasis_log
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
    return True

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@APP.route('/exposure', methods=["POST","GET"])
@helpers.oasis_log
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
        if request.method == 'GET':
            return '''<!doctype html><head><title>Upload new File</title>
            </head>
            <h1>Upload new File</h1>
            <form action="" method=post enctype=multipart/form-data>
            <p><input type=file name=file>
            <input type=submit value=Upload></form>'''

        upfile = request.files['file']
        if upfile and allowed_file(upfile.filename):
            #Validate tar file.
            #if validate_exposure_tar(file.name):
            #Since file is allowed then must have gzip extension.         
            filename = str(uuid.uuid4())
            filepath = os.path.join(EXPOSURE_DATA_DIRECTORY, filename) + DATA_FILE_SUFFIX
            upfile.save(filepath)
            #Validate the exposure tar file contents.
            if validate_exposure_tar(filepath):
                #Un tar the file.
                tar = tarfile.open(filepath)
                #tarnamelist = tar.getnames()
                #for name in tarnamelist:
                #    pass
                    #Generate a list of all the files to use chmod and dos2linux cmd on
                    #os.chmod( file_path , 0777)
                    #dos2unixcmd = 'dos2unix -q ' + file_path
                    #try:
                    #    os.system(dos2unixcmd)
                    #except Exception as e:
                    #    msg = 'Error uploading {0} on dos2unix command : {1}'.format(file_path, e)                              
                
                #ToDo replace extractAll with safe_extract method.
                if not os.path.exists(UPLOAD_DATA_DIRECTORY):
                    os.makedirs(UPLOAD_DATA_DIRECTORY)
                dirname = UPLOAD_DATA_DIRECTORY + "/" + filename
                os.mkdir(dirname)      
                tar.extractall(dirname)
                tar.close()

                # Check the content, and if invalid delete

                size_in_bytes = os.path.getsize(filepath)
                created_date = time.ctime(os.path.getctime(filepath))

                exposure = {
                    "location": dirname,
                    "size": size_in_bytes,
                    "created_date": created_date
                }  

                response = jsonify({'exposures': [exposure]})
           
            else:
                #File uploaded not a valid exposure tar.
                #Should log this in case user queries support about errors.
                print("Invalid exposure tar file uploaded see function validate_exposure_tar for format")
                #Remove invalid tar file.
                os.remove(filepath)
                response = Response(status=HTTP_RESPONSE_INTERNAL_ERROR)                  
        else:
            #Not a gzip tar file extension, return error.
            response = Response(status=HTTP_RESPONSE_INTERNAL_ERROR)    

    except:
        print "Error in post_lookup"
        print traceback.format_exc()
        response = Response(status=HTTP_RESPONSE_INTERNAL_ERROR)

    return response

@APP.route('/exposure', defaults={'location': None}, methods=["DELETE"])
@APP.route('/exposure/<location>', methods=["DELETE"])
@helpers.oasis_log

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
        if location is None:

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
@helpers.oasis_log
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
    result = CELERY.send_task("tasks.start_analysis", ["ANALYSIS_SETTINGS_JSON"])
    task_id = result.task_id
    return jsonify({'location': task_id})
    
@APP.route('/analysis_status/<location>', methods=["GET"])
@helpers.oasis_log
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
            outputs_summary_location:
                type: string
                description: The location of the analysis outputs.
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
    result = CELERY.AsyncResult(location)
    status = result.status
    return jsonify({'status': status})

@APP.route('/analysis_status', methods=["DELETE"])
@APP.route('/analysis_status/<location>', methods=["DELETE"])
@helpers.oasis_log
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

@APP.route('/outputs/<location>', methods=["GET"])
@helpers.oasis_log
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
    return True

@APP.route('/outputs', methods=["DELETE"])
@APP.route('/outputs/<location>', methods=["DELETE"])
@helpers.oasis_log
def delete_outputs(location):
    """
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
    return True

@APP.route("/spec")
@helpers.oasis_log
def spec():
    swag = swagger(APP)
    swag['info']['version'] = "0.1"
    swag['info']['title'] = "Oasis API"
    return jsonify(swag)

@APP.route('/healthcheck', methods=['GET'])
@helpers.oasis_log
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
    return (len(members) == 9) and \
        (sum(1 for member in members if os.path.basename(member.name) == 'events.bin') == 1) and \
        (sum(1 for member in members if os.path.basename(member.name) == 'fm_xref.bin') == 1) and \
        (sum(1 for member in members if os.path.basename(member.name) == 'items.bin') == 1) and \
        (sum(1 for member in members if os.path.basename(member.name) == 'coverages.bin') == 1) and \
        (sum(1 for member in members if os.path.basename(member.name) == 'fmsummaryxref.bin') == 1) and \
        (sum(1 for member in members if os.path.basename(member.name) == 'fm_programme.bin') == 1) and \
        (sum(1 for member in members if os.path.basename(member.name) == 'fm_policytc.bin') == 1) and \
        (sum(1 for member in members if os.path.basename(member.name) == 'fm_profile.bin') == 1) and \
        (sum(1 for member in members if os.path.basename(member.name) == 'gulsummaryxref.bin') == 1)
