#!/bin/bash

LOG_DIR='/var/log/oasis/'
LOG_TOX=$LOG_DIR'test_OasisPlatform.log'
LOG_FLAKE=$LOG_DIR'pep8_OasisPlatform.log'
LOG_COV=$LOG_DIR'coverage_OasisPlatform.log'

BUILD_OUTPUT_DIR='/tmp/output/'


# Install requirements && build
    set -exu
    pip install -r requirements.txt


# Unit testing
    find /home/ -name __pycache__ | xargs -r rm -rfv
    find /home/ -name "*.pyc" | xargs -r rm -rfv
    tox | tee $LOG_TOX

    set +exu
    TOX_FAILED=$(cat $LOG_TOX | grep -ci 'ERROR: InvocationError')
    set -exu
    if [ $TOX_FAILED -ne 0 ]; then 
        echo "Unit testing failed - Exiting build"
        exit 1
    fi 

 
# Code Standards report
    flake8 | tee $LOG_FLAKE


# Coverate report 
    coverage combine
    coverage report  -i src/*/*.py src/*.py > $LOG_COV
