import pytest
import socket
import json
import os
import configparser
import unittest

from oasislmf.api_client.client_manager import APIClient


# ------------ load config -------------------- #

config = configparser.ConfigParser()
config.read('test-conf.ini')
cli_case_override = pytest.config.getoption("--test-case")





# --- Test Paramatization --------------------------------------------------- #

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





# --- API connection Fixture ------------------------------------------------ #

@pytest.fixture(scope="module", params=test_cases)
def session_fixture(request):
    server_addr = config.get('server', 'API_HOST')
    server_port = config.get('server', 'API_PORT')
    server_vers = config.get('server', 'API_VERS')
    server_user = config.get('server', 'API_USER')
    server_pass = config.get('server', 'API_PASS')

    print(request.param)
    try:
        server_url  = 'http://{}:{}'.format(socket.gethostbyname(server_addr), server_port)
    except Exception:
        server_url  = 'http://{}:{}'.format('localhost', server_port)
    session = APIClient(server_url, server_vers, server_user, server_pass)

    print(session.api.tkn_access)
    
    return (request.param, session)



# --- Test Case Fixture ----------------------------------------------------- #

@pytest.fixture(scope="module")
def case_fixture(session_fixture):
    case, session = session_fixture
    case_dir = case[1]
    ids = {}


    ###  Add or find model
    _model = {
        'supplier_id': config.get(test_model, 'SUPPLIER_ID'),
        'model_id':    config.get(test_model, 'MODEL_ID'),
        'version_id':  config.get(test_model, 'VERSION_ID'),
    }

    r_model = session.models.search(_model)
    if (len(r_model.json()) < 1):
        # Model not found - Add new model
        r_model = session.models.create(**_model)
        ids['model'] = r_model.json()['id']
    else:
        # Model found - Use result of search
        ids['model'] = r_model.json()[0]['id']

    ### Create Portfolio 
    loc_fp      = case_dir + '/location.csv' if os.path.isfile(case_dir + '/location.csv') else None
    acc_fp      = case_dir + '/account.csv'  if os.path.isfile(case_dir + '/account.csv') else None
    info_fp     = case_dir + '/ri_info.csv'  if os.path.isfile(case_dir + '/ri_info.csv') else None
    scope_fp    = case_dir + '/ri_scope.csv'  if os.path.isfile(case_dir + '/ri_scope.csv') else None
    r_portfoilio = session.upload_inputs(
        portfolio_name='Integration_test_{}_{}'.format(test_model, case),
        location_fp=loc_fp,
        accounts_fp=acc_fp,
        ri_info_fp=info_fp,
        ri_scope_fp=scope_fp)
    ids['portfoilio'] = r_portfoilio['id']


    ### Create analysis
    settings_fp = case_dir + '/settings.json'  if os.path.isfile(case_dir + '/settings.json') else None
    r_analysis = session.create_analysis(
        analysis_name='Integration_test_{}_{}'.format(test_model, case),
        portfolio_id=ids['portfoilio'],
        model_id=ids['model'],
        analysis_settings_fp=settings_fp)
    ids['analysis'] = r_analysis['id']

    return session, case, ids




# --- Test Fucntions -------------------------------------------------------- #

def test_connection(case_fixture):
    session, case, ids = case_fixture
    assert session.api.health_check().ok
    

def test_uploaded_files(case_fixture):
    session, case, ids = case_fixture
    analysis = session.analyses.get(ids['analysis'])
    portfoilio = session.portfolios.get(ids['portfoilio'])

    assert portfoilio.ok
    assert analysis.ok
    assert analysis.json()['status'] == 'NEW'

    print(analysis.json())
    print(portfoilio.json())

    #if loc_fp:
    #    self.assertTrue(portfoilio_info['location_file'] is not None)
    #if acc_fp:
    #    self.assertTrue(portfoilio_info['accounts_file'] is not None)
    #if info_fp:
    #    self.assertTrue(portfoilio_info['reinsurance_info_file'] is not None)
    #if scope_fp:
    #    self.assertTrue(portfoilio_info['reinsurance_source_file'] is not None)



def test_generate_input_files(case_fixture):
    session, case, ids = case_fixture
    analysis = session.analyses.get(ids['analysis'])
    if (analysis.json()['status'] not in ['NEW']):
        pytest.skip('setup error in prevous step')


    generate_input = session.run_generate(ids['analysis'])
    analysis = session.analyses.get(ids['analysis'])
    assert analysis.ok
    assert analysis.json()['status'] == 'READY'
    assert analysis.json()['input_generation_traceback_file'] == None

 


def test_expected_input_files(case_fixture):
    session, case, ids = case_fixture
    analysis = session.analyses.get(ids['analysis'])
    if (analysis.json()['status'] not in ['READY']):
        pytest.skip('Error in file Generation step')

    input_files_uri = '{}{}/{}'.format(
        session.analyses.input_file.url_endpoint,
        ids['analysis'],
        session.analyses.input_file.url_resource)

    assert analysis.json()['input_file'] == input_files_uri



def test_analysis_run(case_fixture):
    session, case, ids = case_fixture
    analysis = session.analyses.get(ids['analysis'])
    if (analysis.json()['status'] not in ['READY']):
        pytest.skip('Error in file Generation step')


    session.run_analysis(ids['analysis'])
    analysis = session.analyses.get(ids['analysis'])
    assert analysis.ok
    assert analysis.json()['status'] == 'RUN_COMPLETED'
    assert analysis.json()['run_traceback_file'] == None


def test_analysis_output(case_fixture):
    session, case, ids = case_fixture
    analysis = session.analyses.get(ids['analysis'])
    if (analysis.json()['status'] not in ['RUN_COMPLETED']):
        pytest.skip('Error in file Generation step')

    output_files_uri = '{}{}/{}'.format(
        session.analyses.output_file.url_endpoint,
        ids['analysis'],
        session.analyses.output_file.url_resource)

    assert analysis.json()['output_file'] == output_files_uri

def test_cleanup(case_fixture):
    session, case, ids = case_fixture
    r_del_analyses   = session.analyses.delete(ids['analysis'])
    r_del_portfolios = session.portfolios.delete(ids['portfoilio'])
    session.api.close()

    assert r_del_analyses.ok
    assert r_del_portfolios.ok

#def test_api_connection(session_fixture):
#    case, session = session_fixture
#    r = session.api.health_check()
#    assert r.ok
#    assert r.text == '{"status":"OK"}'

