#!/bin/bash
set -e

# Set the ini file path 
export OASIS_API_INI_PATH="./conf.ini"

wait-for-it ${OASIS_API_SERVER_DB_HOST}:${OASIS_API_SERVER_DB_PORT} -t 60
wait-for-it ${OASIS_API_CELERY_DB_HOST}:${OASIS_API_CELERY_DB_PORT} -t 60
wait-for-it ${OASIS_API_RABBIT_HOST}:${OASIS_API_RABBIT_PORT} -t 60
python manage.py migrate

exec "$@"
