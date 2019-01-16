import pytest
import socket 
import json
import os.path 
from oasislmf.api_client.client_manager import APIClient



TEST_RESOURCE_FILE = {
    'lookup_settings': [{'PerilCodes': {'type': 'dictionary',
    'values': {'WW1': 'Windstorm with storm surge',
     'WW2': 'Windstorm w/o storm surge'}}}],
 'model_settings': [{'event_set': {'default': 'P',
    'desc': 'Either Probablistic or Historic',
    'name': 'Event Set',
    'type': 'dictionary',
    'values': {'H': 'Historic', 'P': 'Proabilistic'}}},
  {'event_occurrence_id': {'default': '1',
    'desc': 'Tooltip for Occurrence selection',
    'name': 'Occurrence Set',
    'type': 'dictionary',
    'values': {'1': 'Long Term', '2': 'Near Term WSST', '3': 'Historic'}}},
  {'peril_wind': {'default': True,
    'desc': 'Run model with Wind Peril',
    'name': 'Wind Peril',
    'type': 'boolean'}},
  {'peril_surge': {'default': False,
    'desc': 'Run model with Surge Peril',
    'name': 'Surge Peril',
    'type': 'boolean'}},
  {'leakage_factor': {'default': 0.5,
    'desc': 'Tooltip for Leakage option',
    'max': 1.0,
    'min': 0.0,
    'name': 'Leakage Factor',
    'type': 'float'}}]}

TEST_ANALYSIS_FILE = {
  'analysis_settings': {'analysis_tag': 13,
  'exposure_location': 'L:',
  'gul_output': True,
  'gul_summaries': [{'aalcalc': True,
    'eltcalc': True,
    'id': 1,
    'lec_output': True,
    'leccalc': {'outputs': {'full_uncertainty_aep': True,
      'full_uncertainty_oep': True},
     'return_period_file': True}}],
  'gul_threshold': 0,
  'il_output': True,
  'il_summaries': [{'aalcalc': True,
    'eltcalc': True,
    'id': 1,
    'lec_output': True,
    'leccalc': {'outputs': {'full_uncertainty_aep': True,
      'full_uncertainty_oep': True},
     'return_period_file': True}}],
  'model_settings': {'event_set': 'P', 'peril_wind': True},
  'model_version_id': 'PiWind',
  'module_supplier_id': 'OasisLMF',
  'number_of_samples': 10,
  'prog_id': 12,
  'source_tag': 'piwind'}}

path_location = os.path.abspath('./piwind/SourceLocOEDPiWind10.csv')
path_account  = os.path.abspath('./piwind/SourceAccOEDPiWind.csv')
#path_info     = os.path.abspath('./piwind/')
#path_scope    = os.path.abspath('./piwind/')

@pytest.fixture(scope="module")
def api_connection():
    # Either localhost or resolve IP of container name (Docker network)  
    try:
        server_ip = socket.gethostbyname('oasisplatform_server_1')
    except gaierror:
        server_ip = socket.gethostbyname('localhost')

    api_connection = APIClient('http://{}:8000'.format(server_ip),
                               'V1', 'admin', 'password')

    #def fin():
    #    print("teardown api_connection")
    #    api_connection.api.close()

    #request.addfinalizer(fin)
    return api_connection  # provide the fixture value


def test_healthcheck(api_connection):
    rsp = api_connection.api.health_check()
    assert rsp.ok
    assert rsp.text == '{"status":"OK"}'

def test_token_refresh(api_connection):
    prev_token = api_connection.api.tkn_access
    rsp = api_connection.api._refresh_token()
    new_token = api_connection.api.tkn_access

    assert rsp.ok
    assert prev_token != new_token
    assert len(new_token) > 100


def test_model_add(api_connection):
    rsp_add_1 = api_connection.models.create(
        'OasisLMF',
        'PiWind-test-1',
        '1')
    assert rsp_add_1.ok

    model_1 = rsp_add_1.json()
    assert model_1['supplier_id'] == 'OasisLMF'
    assert model_1['model_id'] == 'PiWind-test-1'
    assert model_1['version_id'] == '1'

    rsp_add_2 = api_connection.models.create(
        'OasisLMF',
        'PiWind-test-2',
        '2')
    assert rsp_add_2.ok
    rsp_add_3 = api_connection.models.create(
        'OasisLMF',
        'PiWind-test-3',
        '3')
    assert rsp_add_3.ok


def test_model_get(api_connection):
    rsp = api_connection.models.get()
    assert rsp.ok
    rsp = api_connection.models.search({'model_id': 'PiWind-test-1'})
    assert rsp.ok


def test_model_resource_file(api_connection):
    rsp = api_connection.models.search({'model_id': 'PiWind-test-1'})
    model = rsp.json()[0]
    print(model)

    # Check 'resource_file' starts empty
    rsp_null = api_connection.models.resource_file.get(model['id'])
    assert rsp_null.status_code == 404

    # Check upload 'resource_file'
    rsp_add_resource = api_connection.models.resource_file.post(model['id'], json.dumps(TEST_RESOURCE_FILE))
    assert rsp_add_resource.ok

    # Check get
    rsp_get_resource = api_connection.models.resource_file.get(model['id'])
    assert rsp_get_resource.ok
    assert rsp_get_resource.json() == TEST_RESOURCE_FILE

    # Check download 

    # Check Upload 

    # del resource
    rsp_del_resource = api_connection.models.resource_file.delete(model['id'])
    assert rsp_del_resource.ok


def test_model_del(api_connection):
    rsp_search = api_connection.models.search({'model_id__contains': 'PiWind-test'})
    assert rsp_search.ok

    for model in rsp_search.json():
        rsp_del = api_connection.models.delete(model['id'])
        assert rsp_del.ok

def test_generate_input(api_connection):
    


    rsp_loc_only = api_connection.portfolios.create('loc_only_test')
    assert rsp_loc_only.ok
    portfolio = rsp_loc_only.json()
    ## Check for empry 
    assert portfolio['accounts_file'] == None 
    assert portfolio['location_file'] == None 
    assert portfolio['reinsurance_info_file'] == None 
    assert portfolio['reinsurance_source_file'] == None 

    rsp_loc_file = api_connection.portfolios.location_file.upload(portfolio['id'], path_location)
    assert rsp_loc_file.ok

    rsp_get_portfoilio = api_connection.portfolios.get(portfolio['id']) 
    assert rsp_get_portfoilio.ok
    portfolio = rsp_get_portfoilio.json()
    

    ## Check for added 
    assert portfolio['location_file'] is not None

    port_loc_only = api_connection.upload_inputs(
             location_fp=path_location,
         )['id']

    # Test file upload
    uploaded_loc = api_connection.portfolios.location_file.get(portfolio['id'])
    with open(path_location) as f:
        local_loc = f.read()

    assert uploaded_loc.text == local_loc

    # Create Analysis 

    # Check find model if added (select vs add) <-- bug must update to oasislmf 1.2.4
    ##rsp_model = api_connection.models.search({'supplier_id': 'OasisIM', 'model_id': 'PiWind', 'version_id': '1')


    rsp_model = api_connection.models.create('OasisIM', 'PiWind', '1')
    assert rsp_model.ok
    model = rsp_model.json()

    rsp_analysis = api_connection.analyses.create('test_analysis', portfolio['id'], model['id'])
    assert rsp_analysis.ok

    #port_acc_only =  api_connection.upload_inputs(
    #         accounts_fp=path_account,
    #     )


    #port_loc_acc = api_connection.upload_inputs(
    #         location_fp=path_location,
    #         accounts_fp=path_account,
    #     )

    #port_loc_acc_scope = api_connection.upload_inputs(
    #         location_fp=path_location,
    #         accounts_fp=path_account,
    #         ri_scope_fp=path_scope,
    #     )

    #port_loc_acc_info = api_connection.upload_inputs(
    #         location_fp=path_location,
    #         accounts_fp=path_account,
    #         ri_info_fp=path_info,
    #     )

    #port_loc_acc_ri = api_connection.upload_inputs(
    #         location_fp=path_location,
    #         accounts_fp=path_account,
    #         ri_info_fp=path_info,
    #         ri_scope_fp=path_scope,
    #     )

