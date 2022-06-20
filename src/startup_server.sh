#!/bin/bash
set -e

# Set the ini file path
export OASIS_API_INI_PATH="./conf.ini"

wait-for-it ${OASIS_SERVER_DB_HOST}:${OASIS_SERVER_DB_PORT} -t 60
wait-for-it ${OASIS_CELERY_DB_HOST}:${OASIS_CELERY_DB_PORT} -t 60
wait-for-it ${OASIS_CELERY_BROKER_URL} -t 60

# Keycloak is bound to a specific hostname which requires us to use the same url to query keycloak in backend that is
# used in the UI for authentication (the JWT will contain the authenticaiton URL). We can't access the external ingress
# hostname but we can map it in the hosts file to point to the ingress service.
if [ -n "$INGRESS_EXTERNAL_HOST" ] && [ -n "$INGRESS_INTERNAL_HOST" ]; then
    sudo update_hosts
fi

if [ "${STARTUP_RUN_MIGRATIONS}" = true ]; then
    python3 manage.py migrate
    # Create default admin if `$OASIS_ADMIN_USER` && `$OASIS_ADMIN_PASS` are set
    python3 set_default_user.py
fi

exec "$@"
