import pytest
import socket
import json
import os
import configparser
import unittest

from oasislmf.api_client.client_manager import APIClient

from parameterized import parameterized


#from backports.tempfile import TemporaryDirectory
#from pandas.util.testing import assert_frame_equal
#from collections import OrderedDict



# ------------ load config -------------------- #

config = configparser.ConfigParser()
config.read('test-conf.ini')
cli_case_override = pytest.config.getoption("--test-case")





# Add?
# override = config.get('default', 'TEST_INPUT_DIR')

#expected_output_dir = os.path.join(cwd, 'expected', 'calc')
if cli_case_override:
    test_examples = cli_case_override
    print('Loading test cases from command line args:')
    print(test_examples)
else:
    test_examples =  config.get('piwind', 'TEST_CASES').split(' ')
    print('Load default test cases from default conf.in:')
    print(test_examples)

base_dir = os.path.dirname(os.path.realpath(__file__))
test_model = config.get('default', 'TEST_MODEL').lower()
input_dir = os.path.join(base_dir, test_model)
output_dir = os.path.join(base_dir, config.get('default', 'TEST_OUTPUT_DIR'))

test_cases = []
for case in test_examples:
    test_cases.append((
        case,
        os.path.join(input_dir, case),
        os.path.join(output_dir, case)
    ))



print (test_cases)
class TestAPI(unittest.TestCase):

    def setUp(self):
        test_model = config.get('default', 'TEST_MODEL').lower()
        self.server_addr = config.get('server', 'API_HOST')
        self.server_port = config.get('server', 'API_PORT')
        self.server_vers = config.get('server', 'API_VERS')
        self.server_user = config.get('server', 'API_USER')
        self.server_pass = config.get('server', 'API_PASS')

        try:
            self.server_url  = 'http://{}:{}'.format(socket.gethostbyname(self.server_addr), self.server_port)
        except Exception:
            self.server_url  = 'http://{}:{}'.format('localhost', self.server_port)
        self.session = APIClient(self.server_url, self.server_vers, self.server_user, self.server_pass)


        t_model = {
            'supplier_id': config.get(test_model, 'SUPPLIER_ID'),
            'model_id':    config.get(test_model, 'MODEL_ID'),
            'version_id':  config.get(test_model, 'VERSION_ID'),
        }

        find_model = self.session.models.search(t_model)
        if (len(find_model.json()) < 1):
            # Model not found - Add new model
            r = self.session.models.create(**t_model)
            if r.ok:
                self.model_info = r.json()
        else:
            # Model found - Use result of search
            self.model_info = find_model.json()[0]

        self.assertEqual(self.model_info['supplier_id'], config.get(test_model, 'SUPPLIER_ID'))
        self.assertEqual(self.model_info['model_id'],    config.get(test_model, 'MODEL_ID'))
        self.assertEqual(self.model_info['version_id'],  config.get(test_model, 'VERSION_ID'))
        self.assertTrue(self.session.api.health_check().ok)


        '''
    def _check_output(self):
        # Fetch Tar output file
        #self.session.download_output(analysis_id, download_path, filename=None, clean_up=False, overwrite=False)

        # with tmp dir:
        #   extract tar

        # list all files in expected_dir


        '''

    ## Main run loop
    @parameterized.expand(test_cases)
    def test_api_examples(self, case, case_dir, expected_dir):
        print("Test case: {}".format(case))

        loc_fp      = case_dir + '/location.csv' if os.path.isfile(case_dir + '/location.csv') else None
        acc_fp      = case_dir + '/account.csv'  if os.path.isfile(case_dir + '/account.csv') else None
        info_fp     = case_dir + '/ri_info.csv'  if os.path.isfile(case_dir + '/ri_info.csv') else None
        scope_fp    = case_dir + '/ri_scope.csv'  if os.path.isfile(case_dir + '/ri_scope.csv') else None
        settings_fp = case_dir + '/settings.json'  if os.path.isfile(case_dir + '/settings.json') else None

        #loc_filepath   = case_dir + '/location.csv' if os.path.isfile(case_dir + '/location.csv') else None
        portfoilio_info = self.session.upload_inputs(
            portfolio_name='Integration_test_{}_{}'.format(test_model, case),
            location_fp=loc_fp,
            accounts_fp=acc_fp,
            ri_info_fp=info_fp,
            ri_scope_fp=scope_fp)

        ## TODO: Check upload of exposures
        portfoilio_info =  self.session.portfolios.get(portfoilio_info['id']).json()
        print(portfoilio_info)
        if loc_fp:
            self.assertTrue(portfoilio_info['location_file'] is not None)
        if acc_fp:
            self.assertTrue(portfoilio_info['accounts_file'] is not None)
        if info_fp:
            self.assertTrue(portfoilio_info['reinsurance_info_file'] is not None)
        if scope_fp:
            self.assertTrue(portfoilio_info['reinsurance_source_file'] is not None)


        #if not settings_fp:
        #    pass
        #    'warn of missing input and skip model exec test'

        analysis_info = self.session.create_analysis(
            analysis_name='Integration_test_{}_{}'.format(test_model, case),
            portfolio_id=portfoilio_info['id'],
            model_id=self.model_info['id'],
            analysis_settings_fp=settings_fp)

        print(analysis_info)
        self.assertEqual(analysis_info['status'], 'NEW')
        self.assertEqual(analysis_info['model'], self.model_info['id'])
        self.assertEqual(analysis_info['portfolio'], portfoilio_info['id'])


        generate_oasis_files = self.session.run_generate(analysis_info['id'])
        analysis_info = self.session.analyses.get(analysis_info['id']).json()
        print(analysis_info)
        self.assertEqual(analysis_info['status'], 'READY')
        self.assertEqual(analysis_info['input_generation_traceback_file'], None)

        oasis_files_uri = '{}/{}/analyses/{}/input_file/'.format(self.server_url, self.server_vers, analysis_info['id'])
        self.assertEqual(
            analysis_info['input_file'], oasis_files_uri)
        ## TODO: Download input tar file and compare with expected 


        self.session.run_analysis(analysis_info['id'])
        ## check status
        ## check 'run_traceback_file' is null
        ## check "output_file": "http://10.10.0.182:8000/v1/analyses/12/input_file/",
        analysis_info = self.session.analyses.get(analysis_info['id']).json()
        print(analysis_info)
        self.assertEqual(analysis_info['status'], 'RUN_COMPLETED')
        self.assertEqual(analysis_info['run_traceback_file'], None)

        output_files_uri = '{}/{}/analyses/{}/output_file/'.format(self.server_url, self.server_vers, analysis_info['id'])
        self.assertEqual(analysis_info['output_file'], output_files_uri)




        
