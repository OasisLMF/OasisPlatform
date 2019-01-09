#!/bin/bash
set -e

# Set the ini file path 
export OASIS_API_INI_PATH="./conf.ini"

wait-for-it ${OASIS_SERVER_DB_HOST}:${OASIS_SERVER_DB_PORT} -t 60
wait-for-it ${OASIS_CELERY_DB_HOST}:${OASIS_CELERY_DB_PORT} -t 60
wait-for-it ${OASIS_RABBIT_HOST}:${OASIS_RABBIT_PORT} -t 60

if [ "${STARTUP_RUN_MIGRATIONS}" = true ]; then
    python manage.py migrate
fi

exec "$@"
