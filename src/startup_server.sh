#!/bin/bash
set -e

# Set the ini file path 
export OASIS_API_INI_PATH="./conf.ini"

wait-for-it ${OASIS_SERVER_DB_HOST}:${OASIS_SERVER_DB_PORT} -t 60
wait-for-it ${OASIS_CELERY_DB_HOST}:${OASIS_CELERY_DB_PORT} -t 60
wait-for-it ${OASIS_CELERY_BROKER_URL} -t 60


if [ "${STARTUP_RUN_MIGRATIONS}" = true ]; then
    python manage.py migrate
    # Create default admin if `$OASIS_ADMIN_USER` && `$OASIS_ADMIN_PASS` are set
    python set_default_user.py
fi

exec "$@"
