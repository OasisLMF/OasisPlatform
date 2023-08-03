#!/bin/bash
set -e

# Set the ini file path
export OASIS_API_INI_PATH="./conf.ini"

wait-for-it ${OASIS_SERVER_DB_HOST}:${OASIS_SERVER_DB_PORT} -t 60
wait-for-it ${OASIS_CELERY_DB_HOST}:${OASIS_CELERY_DB_PORT} -t 60
wait-for-it ${OASIS_CELERY_BROKER_URL} -t 60

if [ "${STARTUP_RUN_MIGRATIONS}" = true ]; then
    # try migration
    set +e
    python3 manage.py migrate 
    exitcode=$?
    migration_is_missing=$(python3 manage.py showmigrations | grep -c '\[ \] 0005_auto_20220510_1103')
 
    # Apply Platform2 compatibility Migration as fallback
    # Fallback migration between plat2 (older) and plat2 (2.2.1+)
    if [ $exitcode -gt 0 ] && [ $migration_is_missing -eq 1 ]; then
        migration-helper.sh
        exitcode=$?
    fi 

    # guard fail if exitcode is non-zero
    if [ $exitcode -gt 0 ]; then 
        exit $exitcode
    fi    
fi

set -e 
# Create default admin if `$OASIS_ADMIN_USER` && `$OASIS_ADMIN_PASS` are set
python3 set_default_user.py

exec "$@"
