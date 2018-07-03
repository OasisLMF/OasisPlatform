#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export PYTHONPATH=$SCRIPT_DIR

# Set the ini file path 
export OASIS_API_INI_PATH="${SCRIPT_DIR}/conf.ini"

# Delete celeryd.pid file - fix que pickup issues on reboot of server
rm -f /home/worker/celeryd.pid

echo "wait for rabbit - $OASIS_RABBIT_HOST:$OASIS_RABBIT_PORT"
./src/utils/wait-for-it.sh "$OASIS_RABBIT_HOST:$OASIS_RABBIT_PORT" -t 60

echo "wait for db - $OASIS_CELERY_DB_HOST:$OASIS_CELERY_DB_PORT"
./src/utils/wait-for-it.sh "$OASIS_CELERY_DB_HOST:$OASIS_CELERY_DB_PORT" -t 60

# Start worker on init
celery worker -A src.model_execution_worker.tasks --detach --loglevel=INFO --logfile="/var/log/oasis/worker.log" -Q "${MODEL_SUPPLIER_ID}-${MODEL_VERSION_ID}-${MODEL_VERSION_ID}"

sleep 5

tail -f /var/log/oasis/worker.log
