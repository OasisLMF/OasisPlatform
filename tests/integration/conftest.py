# content of conftest.py
import pytest

def pytest_addoption(parser):
    parser.addoption( '--test-case', required=False,  dest='data_case',
        action='store', nargs='+', default=None, 
        help='The directory of data files used to test a model.')
