# content of conftest.py
# import pytest

def pytest_addoption(parser):
    parser.addoption(
        '--test-case', required=False, dest='data_case',
        action='store', nargs='+', default=None,
        help='The directory of data files used to test a model.'
    )
    parser.addoption(
        '--test-output', required=False, dest='data_test',
        action='store_true', default=False,
        help='The directory of data files used to test a model.'
    )
    parser.addoption(
        '--config', required=False, dest='test_conf',
        action='store', nargs='?', default='/var/oasis/test/conf.ini',
        help='File path to test configuration ini'
    )

def pytest_configure(config):
    import os
    if config.getoption('--test-case'):
        os.environ["PY_TEST_CASE"] = " ".join(config.getoption('--test-case'))
    if config.getoption('--test-output'):
        os.environ["PY_CHECK_OUTPUT"] = 'True'
    if config.getoption('--config'):
        os.environ["PY_CONFIG"] = config.getoption('--config') 
