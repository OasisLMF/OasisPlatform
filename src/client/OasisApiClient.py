import csv
import inspect
import jsonpickle
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


    INPUTS_FILES = {
            'coverages', 
            'events', 
            'fm_policytc',  
            'fm_profile', 
            'fm_programme', 
            'fm_xref', 
            'fmsummaryxref', 
            'gulsummaryxref', 
            'items'} 

    CONVERSION_TOOLS = {
            'coverages' : 'coveragetobin',
            'events' : 'evetobin',
            'fm_policytc' : 'fmpolicytctobin',  
            'fm_profile' : 'fmprofiletobin', 
            'fm_programme' : 'fmprogrammetobin', 
            'fm_xref' : 'fmxreftobin', 
            'fmsummaryxref' : 'fmsummaryxreftobin', 
            'gulsummaryxref' : 'gulsummaryxreftobin',
            'items' : "itemtobin"} 

    TAR_FILE = "inputs.tar.gz"

    # Analysis settings files
    GENERAL_SETTINGS_FILE = "general_settings.csv"
    MODEL_SETTINGS_FILE = "model_settings.csv"
    GUL_SUMMARIES_FILE = "gul_summaries.csv"
    IL_SUMMARIES_FILE = "il_summaries.csv"

    DOWNLOAD_CHUCK_SIZE_IN_BYTES = 1024

    def __init__(self, oasis_api_url, logger):  
        '''
        Construct the client.
        Args:
            oasis_api_url: the URL for the API.
            logger: the logger.
        '''
          
        self._oasis_api_url = oasis_api_url
        self._logger = logger
        # Check that the conversion tools are available
        for tool in self.CONVERSION_TOOLS.itervalues():
            if shutilwhich.which(tool) == "":
                error_message ="Failed to find conversion tool: {}".format(tool) 
                self._logger.error(error_message)
                raise Exception(error_message)
        # Check the API
        request_url = "/healthcheck"
        response = requests.get(self._oasis_api_url + request_url)
        if response.status_code != 200:
            self._logger.error("GET {} failed: {}".format(request_url, str(response.status_code)))
            raise Exception("API healthcheck failed.")

    def upload_inputs_from_directory(self, directory, do_validation=False):
        '''
        Upload the CSV files from a specified directory.
        Args:
            directory (string): the directory containting the CSVs.
            do_validation (bool): if True, validate the data intrgrity
        Returns:
            The location of the uploaded inputs.
        '''
        frame = inspect.currentframe()
        func_name = inspect.getframeinfo(frame)[2]
        self._logger.info("STARTED: {}".format(func_name))
        args, _, _, values = inspect.getargvalues(frame)
        for i in args:
            if i == 'self': continue
            self._logger.info("{}={}".format(i, values[i]))
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
            raise Exception("Failed to save exposure.")
        exposure_location = response.json()['exposures'][0]['location'] 
        self._logger.debug("Uploaded exposure. Location: " + exposure_location)

        # Tidy up
        self._clean_directory(directory)


        end = time.time()
        self._logger.info("COMPLETED: {} in {}s".format(func_name, round(end - start,2)))

        # Return the location of the uploaded inputs
        return exposure_location

    def run_analysis(self, analysis_settings_json, input_location, outputs_directory, do_clean=False):
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
        frame = inspect.currentframe()
        func_name = inspect.getframeinfo(frame)[2]
        self._logger.info("STARTED: {}".format(func_name))
        args, _, _, values = inspect.getargvalues(frame)
        for i in args:
            if i == 'self': continue
            self._logger.info("{}={}".format(i, values[i]))

        start = time.time()

        request_url ="/analysis/"  + input_location 
        response = requests.post(
            self._oasis_api_url + request_url,
            json = analysis_settings_json)
        if response.status_code != 200:
            self._logger.error("POST {} failed: {}".format(request_url, str(response.status_code)))
            raise Exception("Failed to start analysis")          
        analysis_status_location =  response.json()['location']
        status = helpers.TASK_STATUS_PENDING
        self._logger.info("Analysis started")
        analysis_poll_interval_in_seconds = 5
        request_url ="/analysis_status/"
        
        while True:
            self._logger.debug("Polling analysis status for: {}".format(analysis_status_location))
            response = requests.get(self._oasis_api_url + request_url + analysis_status_location)
            if response.status_code != 200:
                raise Exception("GET analysis status failed: {}".format(response.status_code))

            self._logger.debug("Response: {}".format(response.json()))
            status = response.json()['status']
            message = response.json()['message']
            self._logger.debug("Analysis status: " + status)
            if status == helpers.TASK_STATUS_SUCCESS:
                break
            if status == helpers.TASK_STATUS_FAILURE:
                error_message = "Analysis failed: {}".format(message)
                self._logger.error(error_message)
                raise Exception(error_message)
            time.sleep(analysis_poll_interval_in_seconds)
        outputs_location = response.json()['outputs_location']
        self._logger.debug("Analysis completed")
        func_name= func_name

        self._logger.debug("Downloading outputs")
        outputs_file = os.path.join(outputs_directory, outputs_location + ".tar.gz")
        self.download_outputs(outputs_location, outputs_file)
        self._logger.debug("Downloaded outputs")

        self._logger.debug("Deleting exposure")
        response = requests.delete(self._oasis_api_url + "/exposure/" + input_location)
        if response.status_code != 200:
            # Do not fail if tidy up fails
            self._logger.warn("DELETE /exposure failed: {}".format(str(response.status_code)))
        self._logger.debug("Deleted exposure")

        self._logger.info("Deleting outputs")
        response = requests.delete(self._oasis_api_url + "/outputs/" + outputs_location)
        if response.status_code != 200:
            # Do not fail if tidy up fails
            self._logger.warn("DELETE /outputs failed: {}".format(str(response.status_code)))
        self._logger.info("Deleted outputs")

        end = time.time()
        self._logger.debug("COMPLETED: OasisApiClient.run_analysis in {}s".format(round(end - start,2)))

    def download_exposure(self,exposure_location, localfile):
        '''
        Download exposure data to a specified local file.
        Args:
            exposure_location (string): The location of the exposure resource.
            localfile (string): The localfile to download to.
        '''
        frame = inspect.currentframe()
        func_name = inspect.getframeinfo(frame)[2]
        self._logger.info("STARTED: {}".format(func_name))
        args, _, _, values = inspect.getargvalues(frame)
        for i in args:
            if i == 'self': continue
            self._logger.info("{}={}".format(i, values[i]))
        start = time.time()

        response = requests.get(
            self._oasis_api_url + "/exposure/" + exposure_location, 
            stream=True)
        if response.status_code != 200:
            exception_message = "GET /exposure failed: {}".format(str(response.status_code)) 
            self._logger.error(exception_message)
            raise Exception(exception_message)
  
        with open(localfile, 'wb') as f:
            for chunk in response.iter_content(chunk_size=self.DOWNLOAD_CHUCK_SIZE_IN_BYTES): 
                if chunk:
                    f.write(chunk)

        end = time.time()
        self._logger.info("COMPLETED: {} in {}s".format(func_name, round(end - start,2)))

    def download_outputs(self, outputs_location, localfile):
        '''
        Download outputs data to a specified local file.
        Args:
            outputs_location (string): The location of the outputs resource.
            localfile (string): The localfile to download to.
        '''
        frame = inspect.currentframe()
        func_name = inspect.getframeinfo(frame)[2]
        self._logger.info("STARTED: {}".format(func_name))
        args, _, _, values = inspect.getargvalues(frame)
        for i in args:
            if i == 'self': continue
            self._logger.info("{}={}".format(i, values[i]))
        start = time.time()

        if os.path.exists(localfile):
            error_message = 'Local file alreday exists: {}'.format(localfile)
            _logger.error(error_message)
            raise Exception(error_message)

        response = requests.get(
            self._oasis_api_url + "/outputs/" + outputs_location, 
            stream=True)
        if response.status_code != 200:
            exception_message = "GET /outputs failed: {}".format(str(response.status_code)) 
            self._logger.error(exception_message)
            raise Exception(exception_message)
  
        with open(localfile, 'wb') as f:
            for chunk in response.iter_content(chunk_size=self.DOWNLOAD_CHUCK_SIZE_IN_BYTES): 
                if chunk:
                    f.write(chunk)

        end = time.time()
        self._logger.info("COMPLETED: {} in {}s".format(func_name, round(end - start,2)))

    def create_analysis_settings_json(self, directory):
        '''
        Generate an analysis settings JSON from a set of
        CSV files in a specified directory.
        Args:
            directory (string): the directory containing the CSV files.
        Returns:
            The analysis settings JSON.
        '''
        frame = inspect.currentframe()
        func_name = inspect.getframeinfo(frame)[2]
        self._logger.info("STARTED: {}".format(func_name))
        args, _, _, values = inspect.getargvalues(frame)
        for i in args:
            if i == 'self': continue
            self._logger.info("{}={}".format(i, values[i]))
        start = time.time()

        if not os.path.exists(directory):
            error_message = "Directory does not exist: {}".format(directory)
            self._logger.error(error_message) 
            raise Exception(error_message)

        general_settings_file = os.path.join(directory, self.GENERAL_SETTINGS_FILE)
        model_settings_file = os.path.join(directory, self.MODEL_SETTINGS_FILE)
        gul_summaries_file = os.path.join(directory, self.GUL_SUMMARIES_FILE)
        il_summaries_file = os.path.join(directory, self.IL_SUMMARIES_FILE)
       
        for file in [general_settings_file, model_settings_file, gul_summaries_file, il_summaries_file]:
            if not os.path.exists(directory):
                error_message = "File does not exist: {}".format(directory)
                self._logger.error(error_message) 
                raise Exception(error_message)

        general_settings = dict()
        with open(general_settings_file, 'rb') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                general_settings[row[0]] = eval("{}('{}')".format(row[2], row[1]))

        model_settings = dict()
        with open(model_settings_file, 'rb') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                model_settings[row[0]] = eval("{}('{}')".format(row[2], row[1]))

        gul_summaries = self._get_summaries(gul_summaries_file)
        il_summaries = self._get_summaries(il_summaries_file)

        analysis_settings = general_settings
        analysis_settings['model_settings'] = model_settings
        analysis_settings['gul_summaries'] = gul_summaries
        analysis_settings['il_summaries'] = il_summaries
        json = jsonpickle.encode(analysis_settings)
        self._logger.info("Analysis settings json: {}".format(json))

        end = time.time()
        self._logger.info("COMPLETED: {} in {}s".format(func_name, round(end - start,2)))

        return json

    def _check_inputs_directory(self, directory_to_check):
        ''' Check the directory state.'''
        file_path = os.path.join(directory_to_check, self.TAR_FILE)
        if os.path.exists(file_path):
            raise Exception("Inputs tar file already exists: {}".format(file_path))
        for file in self.INPUTS_FILES:
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
        for file in self.INPUTS_FILES:
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
            for file in self.INPUTS_FILES:
                bin_file = file + ".bin"
                tar.add(bin_file)
        os.chdir(original_cwd)

    def _clean_directory(self, directory_to_check):
        ''' Clean the tar and binary files. '''
        file_path = os.path.join(directory_to_check, self.TAR_FILE)
        if os.path.exists(file_path):
            os.remove(file_path)
        for file in self.INPUTS_FILES:
            file_path = os.path.join(directory_to_check, file + ".bin")
            if os.path.exists(file_path):
                os.remove(file_path)

    def _get_summaries(self, summary_file):
        ''' Get a list representation of a summary file. '''
        summaries_dict = dict()
        with open(summary_file, 'rb') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                id = int(row[0]) 
                if not summaries_dict.has_key(id):
                    summaries_dict[id] = dict()
                    summaries_dict[id]['leccalc'] = dict()
                if row[1].startswith('leccalc'):
                    summaries_dict[id]['leccalc'][row[1]] = bool(row[2]) 
                else:
                    summaries_dict[id][row[1]] = bool(row[2])
        summaries = list()
        for id in summaries_dict.keys():
            summaries_dict[id]['id'] = id
            summaries.append(summaries_dict[id])

        return summaries
