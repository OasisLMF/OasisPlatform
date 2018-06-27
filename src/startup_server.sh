#!/bin/bash
set -e

# Set the ini file path 
export OASIS_API_INI_PATH="./conf.ini"

wait-for-it ${OASIS_API_DB_HOST}:${OASIS_API_DB_PORT}

exec $@
