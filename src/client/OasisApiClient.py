import os
import subprocess
import traceback
import logging
import tarfile
import time
import requests
import shutilwhich
import requests_toolbelt
from requests_toolbelt.multipart.encoder import MultipartEncoder
from common import helpers
from shutil import which

class OasisApiClient(object):
    '''
    Client for Oasis API
    '''

    FILES = {
            "items", "coverages",  'summaryxref',
            'fm_programme', 'fm_policytc',  'fm_profile'} 

    CONVERSION_TOOLS = {
            "items" : "itemtobin", 
            "coverages": "coveragetobin",  
            'summaryxref': 'summaryxreftobin',
            'fm_programme': 'fmprogrammetobin', 
            'fm_policytc': 'fmpolicytctobin',  
            'fm_profile': 'fmprofiletobin'} 

    TAR_FILE = "inputs.tar.gz"

    def __init__(self, oasis_api_url, logger):    
        self._oasis_api_url = oasis_api_url
        self._logger = logger
        # Check that the conversion tools are available
        for tool in self.CONVERSION_TOOLS.itervalues():
            if shutilwhich.which(tool) == "":
                error_message ="Failed to find conversion tool: {}".format(tool) 
                self._logger.error(error_message)
                raise Exception(error_message)    

    def upload_inputs_from_directory(self, directory, do_validation=False):
        '''
        Upload the CSV files from a specified directory.
        Args:
            directory (string): the directory containting the CSVs.
            do_validation (bool): if True, validate the data intrgrity
        Returns:
            The location of the uploaded inputs.
        '''

        self._logger.debug("STARTED: OasisApiClient.upload_inputs_from_directory")
        start = time.time()
                
        self._check_inputs_directory(directory)
        if do_validation:
            self._validate_inputs(directory)
        self._create_binary_files(directory)
        self._create_tar_file(directory)

        self._logger.debug("Uploading inputs")
        tar_file = 'inputs.tar.gz' 
        inputs_tar_to_upload =  os.path.join(directory, tar_file)
        inputs_multipart_data = MultipartEncoder( \
            fields={'file': (tar_file, open(inputs_tar_to_upload, 'rb'), 'text/plain')})
        request_url = "/exposure"
        response = requests.post(
            self._oasis_api_url + request_url,
            data=inputs_multipart_data,
            headers={'Content-Type': inputs_multipart_data.content_type})
        if response.status_code != 200:
            self._logger.error("POST {} failed: {}".format(request_url, str(response.status_code)))
            throw Exception("Failed to save exposure.")
        exposure_location = response.json()['exposures'][0]['location'] 
        self._logger.debug("Uploaded exposure. Location: " + exposure_location)

        # Tidy up
        self._clean_directory(directory)

        end = time.time()
        self._logger.debug("COMPLETED: OasisApiClient.upload_inputs_from_directory in {}s".format(round(end - start,2)))

        # Return the location of the uploaded inputs
        return exposure_location

    def run_analysis(self, analysis_settings_json, inputs_location, outputs_directory, do_clean=False):
        '''
        Run an analysis.
        Args:
            analysis_setting_json (string): The analysis settings, as JSON.
            inputs_location: The location of the inputs resource.
            outputs_directory: The local directory to save the outputs.
            do_clean (bool): if True, remove the inputs and outputs resources.
        Returns:
            The location of the uploaded inputs.
        '''
        
        self._logger.debug("STARTED: OasisApiClient.run_analysis")
        start = time.time()

        request_url ="/analysis" 
        response = requests.post(
            self._oasis_api_url + request_url, #+ inputs_location,
            json = analysis_settings_json)
        if response.status_code != 200:
            self._logger.error("POST {} failed: {}".format(request_url, str(response.status_code)))
            raise Exception("Failed to start analysis")          
        analysis_status_location =  response.json()['location']
        status = helpers.TASK_STATUS_PENDING
        print "Analysis started"
        analysis_poll_interval_in_seconds = 5
        request_url ="/analysis_status/"
        
        while True:
            self._logger.debug("Polling analysis status for: {}".format(analysis_status_location))
            response = requests.get(self._oasis_api_url + request_url + analysis_status_location)
            self._logger.debug("Response: {}".format(response.json()))
            status = response.json()['status']
            message = response.json()['message']
            self._logger.debug("Analysis status: " + status)
            if status == helpers.TASK_STATUS_SUCCESS:
                break
            if status == helpers.TASK_STATUS_FAILURE:
                error_message = "Analysis failed: {}".format(message)
                self._logger.error(error_message)
                raise Excepion(error_message)
            time.sleep(analysis_poll_interval_in_seconds)
        outputs_location = response.json()['outputs_location']
        self._logger.debug("Analysis completed")

        self._logger.debug("Downloading outputs")
        response = requests.get(self._oasis_api_url + "/outputs/" + outputs_location)
        if response.status_code != 200:
            self._logger.error("GET /outputs failed: {}".format(str(response.status_code)))
            raise Exception("Failed to download outputs")
        self._logger.debug("Downloaded outputs")

        self._logger.debug("Deleting exposure")
        response = requests.delete(self._oasis_api_url + "/exposure/" + inputs_location)
        if response.status_code != 200:
            # Do not fail if tidy up fails
            self._logger.warn("DELETE /exposure failed: {}".format(str(response.status_code)))
        self._logger.debug("Deleted exposure")

        print "Deleting outputs"
        response = requests.delete(self._oasis_api_url + "/outputs/" + outputs_location)
        if response.status_code != 200:
            # Do not fail if tidy up fails
            self._logger.warn("DELETE /outputs failed: {}".format(str(response.status_code)))
        print "Deleted outputs"

        end = time.time()
        self._logger.debug("COMPLETED: OasisApiClient.run_analysis in {}s".format(round(end - start,2)))

    def _check_inputs_directory(self, directory_to_check):
        ''' Check the directory state.'''
        file_path = os.path.join(directory_to_check, self.TAR_FILE)
        if os.path.exists(file_path):
            raise Exception("Inputs tar file already exists: {}".format(file_path))
        for file in self.FILES:
            file_path = os.path.join(directory_to_check, file + ".csv")
            if not os.path.exists(file_path):
                raise Exception("Failed to find {}".format(file_path))
            file_path = os.path.join(directory_to_check, file + ".bin")
            if os.path.exists(file_path):
                raise Exception("Binary file already exists: {}".format(file_path))

    def _validate_inputs(self, directory):
        ''' Validate the input files.'''
        #TODO
        test = 1

    def _create_binary_files(self, directory):
        ''' Create the binary files.'''
        for file in self.FILES:
            conversion_tool = self.CONVERSION_TOOLS[file]
            input_file_path = os.path.join(directory, file + ".csv")
            output_file_path = os.path.join(directory, file + ".bin")
            command = "{} < {} > {}".format(conversion_tool, input_file_path, output_file_path)
            self._logger.debug("Running command: {}".format(command))
            proc = subprocess.Popen(command, shell=True)
            proc.wait()
            if proc.returncode != 0:
                self._logger.exception("Failed to convert {}".format(input_file_path))
                is_okay = False
                break
    
    def _create_tar_file(self, directory):
        ''' Package the binaries in a gzipped tar. '''
        original_cwd = os.getcwd()
        os.chdir(directory)
        with tarfile.open(self.TAR_FILE, "w:gz") as tar:
            for file in self.FILES:
                bin_file = file + ".bin"
                tar.add(bin_file)
        os.chdir(original_cwd)

    def _clean_directory(self, directory_to_check):
        ''' Clean the tar and binary files. '''
        file_path = os.path.join(directory_to_check, self.TAR_FILE)
        if os.path.exists(file_path):
            os.remove(file_path)
        for file in self.FILES:
            file_path = os.path.join(directory_to_check, file + ".bin")
            if os.path.exists(file_path):
                os.remove(file_path)
