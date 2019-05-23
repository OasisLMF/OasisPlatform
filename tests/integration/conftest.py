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
