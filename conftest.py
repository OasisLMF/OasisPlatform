"""pytest configuration"""


def pytest_addoption(parser):
    parser.addoption(
        '--update-expected', action='store_true', default=False,
        help='If True, update all the expected files, overwriting them if they exist. Default: False.'
    )
