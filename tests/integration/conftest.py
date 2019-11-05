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
        '--test-model', required=False, dest='test-model',
        action='store', nargs='?', default=None,
        help='Model to test from `conf.ini`'
    )
    parser.addoption(
        '--test-retry', required=False, dest='test-retry',
        action='store', nargs='?', default=1, type=int,
        help='Number of times to re-submit API tests'
    )
    parser.addoption(
        '--config', required=False, dest='test_conf',
        action='store', nargs='?', default='/var/oasis/test/conf.ini',
        help='File path to test configuration ini'
    )


def pytest_configure(config):
    import os
    if config.getoption('--test-case'):
        os.environ["PY_TEST_CASE"] = " ".join(config.getvalue('--test-case'))
    if config.getoption('--test-output'):
        os.environ["PY_TEST_OUTPUT"] = 'True'
    if config.getoption('--test-model'):
        os.environ["PY_TEST_MODEL"] = config.getvalue('--test-model')
    if config.getoption('--test-retry'):
        os.environ["PY_TEST_RETRY"] = str(config.getvalue('--test-retry'))
    if config.getoption('--config'):
        os.environ["PY_CONFIG"] = config.getvalue('--config')
