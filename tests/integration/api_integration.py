import pytest
import socket
import os
import tarfile
import configparser
import pandas as pd

from pandas.util.testing import assert_frame_equal

from oasislmf.api_client.client_manager import APIClient


# ------------ load config -------------------- #

cli_case_override = pytest.config.getoption("--test-case")
test_conf_ini = pytest.config.getoption("--config")

print(test_conf_ini)
print(os.path.abspath(test_conf_ini))

config = configparser.ConfigParser()
config.read(os.path.abspath(test_conf_ini))


def get_path(section, var, config=config):
    try:
        return os.path.abspath(config.get(section, var))
    except configparser.NoOptionError:
        return None


def check_expected(result_path, expected_path):
    comparison_list = []
    cwd = os.getcwd()
    os.chdir(expected_path)
    for rootdir, _, filelist in os.walk('.'):
        for f in filelist:
            comparison_list.append(os.path.join(rootdir[2:], f))
    
    print(comparison_list)
    os.chdir(cwd)
    for csv in comparison_list:
        print(csv)
        df_expect = pd.read_csv(os.path.join(expected_path, csv))
        df_found = pd.read_csv(os.path.join(result_path, csv))
        assert_frame_equal(df_expect, df_found)
    

# --- Test Paramatization --------------------------------------------------- #


if cli_case_override:
    test_cases = cli_case_override
    print('Loading test cases from command line args:')
else:
    test_cases = config.get('piwind', 'RUN_TEST_CASES').split(' ')
    print('Load default test cases from default conf.in:')

base_dir = os.path.dirname(os.path.abspath(test_conf_ini))
os.chdir(base_dir)
test_model = config.get('default', 'TEST_MODEL').lower()


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
        server_url = 'http://{}:{}'.format(socket.gethostbyname(server_addr), server_port)
    except Exception:
        server_url = 'http://{}:{}'.format('localhost', server_port)
    session = APIClient(server_url, server_vers, server_user, server_pass)

    print(session.api.tkn_access)
    
    return request.param, session


# --- Test Case Fixture ----------------------------------------------------- #


@pytest.fixture(scope="module")
def case_fixture(session_fixture):
    case, session = session_fixture
    ids = {}
    
    #  Add or find model
    _model = {
        'supplier_id': config.get(test_model, 'SUPPLIER_ID'),
        'model_id':    config.get(test_model, 'MODEL_ID'),
        'version_id':  config.get(test_model, 'VERSION_ID'),
    }

    r_model = session.models.search(_model)
    if len(r_model.json()) < 1:
        # Model not found - Add new model
        r_model = session.models.create(**_model)
        ids['model'] = r_model.json()['id']
    else:
        # Model found - Use result of search
        ids['model'] = r_model.json()[0]['id']

    # Create Portfolio
    loc_fp = get_path('piwind.{}'.format(case), 'LOC_FILE')
    print(loc_fp)
    assert os.path.isfile(loc_fp)
    acc_fp = get_path('piwind.{}'.format(case), 'ACC_FILE')
    inf_fp = get_path('piwind.{}'.format(case), 'INF_FILE')
    scp_fp = get_path('piwind.{}'.format(case), 'SCP_FILE')

    r_portfolio = session.upload_inputs(
        portfolio_name='Integration_test_{}_{}'.format(test_model, case),
        location_fp=loc_fp,
        accounts_fp=acc_fp,
        ri_info_fp=inf_fp,
        ri_scope_fp=scp_fp)
    ids['portfolio'] = r_portfolio['id']

    # Create analysis
    settings_fp = get_path('piwind.{}'.format(case), 'SETTINGS_RUN')
    assert os.path.isfile(settings_fp)
    r_analysis = session.create_analysis(
        analysis_name='Integration_test_{}_{}'.format(test_model, case),
        portfolio_id=ids['portfolio'],
        model_id=ids['model'])

    ids['analysis'] = r_analysis['id']
    r_upload_settings = session.analyses.settings_file.upload(ids['analysis'], settings_fp, 'application/json')
    assert r_upload_settings.ok

    return session, case, ids

# --- Test Fucntions -------------------------------------------------------- #


def test_connection(case_fixture):
    session, case, ids = case_fixture
    assert session.api.health_check().ok
    

def test_uploaded(case_fixture):
    session, case, ids = case_fixture
    analysis = session.analyses.get(ids['analysis'])
    portfolio = session.portfolios.get(ids['portfolio'])

    assert portfolio.ok
    assert analysis.ok
    assert analysis.json()['status'] == 'NEW'

    print(analysis.json())
    print(portfolio.json())


def test_generate(case_fixture):
    session, case, ids = case_fixture
    analysis = session.analyses.get(ids['analysis'])
    if analysis.json()['status'] not in ['NEW']:
        pytest.skip('setup error in prevous step')

    generate_input = session.run_generate(ids['analysis'])
    analysis = session.analyses.get(ids['analysis'])
    assert analysis.ok
    assert analysis.json()['status'] == 'READY'
    assert analysis.json()['input_generation_traceback_file'] is None
 

def test_generated_files(case_fixture):
    session, case, ids = case_fixture
    analysis = session.analyses.get(ids['analysis'])
    if analysis.json()['status'] not in ['READY']:
        pytest.skip('Error in file Generation step')

    output_dir = os.path.abspath(config.get('default','TEST_OUTPUT_DIR'))
    download_to = '{0}/{1}_input.tar.gz'.format(output_dir, case, ids['analysis'])
    extract_to = os.path.join(output_dir, case, 'input')

    if os.path.isfile(download_to):
        os.remove(download_to)
    r = session.analyses.input_file.download(ids['analysis'], download_to)
    assert r.ok

    tar_object = tarfile.open(download_to)
    csv_only = [f for f in tar_object.getmembers() if '.csv' in f.name]
    tar_object.extractall(path=extract_to, members=csv_only)
    tar_object.close()
    if os.path.isfile(download_to):
       os.remove(download_to) 


def test_analysis_run(case_fixture):
    session, case, ids = case_fixture
    analysis = session.analyses.get(ids['analysis'])
    if analysis.json()['status'] not in ['READY']:
        pytest.skip('Error in file Generation step')

    session.run_analysis(ids['analysis'])
    analysis = session.analyses.get(ids['analysis'])
    assert analysis.ok
    assert analysis.json()['status'] == 'RUN_COMPLETED'
    assert analysis.json()['run_traceback_file'] is None


def test_analysis_output(case_fixture):
    session, case, ids = case_fixture
    analysis = session.analyses.get(ids['analysis'])
    if analysis.json()['status'] not in ['RUN_COMPLETED']:
        pytest.skip('Error in file Generation step')

    if not get_path(test_model, 'EXPECTED_OUTPUT_DIR'):
        pytest.skip('Expected data missing')

    expected_results = os.path.join(get_path(test_model, 'EXPECTED_OUTPUT_DIR'), case, 'output')
    output_dir = os.path.abspath(config.get('default','TEST_OUTPUT_DIR'))
    download_to = '{0}/{1}_output.tar.gz'.format(output_dir, case, ids['analysis'])
    extract_to = os.path.join(output_dir, case)

    if os.path.isfile(download_to):
        os.remove(download_to)
    r = session.analyses.output_file.download(ids['analysis'], download_to)
    assert r.ok
    
    tar_object = tarfile.open(download_to)
    csv_only = [f for f in tar_object.getmembers() if '.csv' in f.name ]
    tar_object.extractall(path=extract_to, members=csv_only)
    tar_object.close()
    
    check_expected(expected_results, os.path.join(extract_to, 'output'))
    if os.path.isfile(download_to):
        os.remove(download_to)


def test_cleanup(case_fixture):
    if not config.getboolean('default', 'CLEAN_UP'):
        pytest.skip('Skip clean up')

    session, case, ids = case_fixture
    r_del_analyses = session.analyses.delete(ids['analysis'])
    r_del_portfolios = session.portfolios.delete(ids['portfolio'])
    session.api.close()

    assert r_del_analyses.ok
    assert r_del_portfolios.ok
