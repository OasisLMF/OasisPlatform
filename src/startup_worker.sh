#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export PYTHONPATH=$SCRIPT_DIR

# Set the ini file path 
export OASIS_INI_PATH="${SCRIPT_DIR}/conf.ini"

# Delete celeryd.pid file - fix que pickup issues on reboot of server
rm -f /home/worker/celeryd.pid

./src/utils/wait-for-it.sh "$OASIS_RABBIT_HOST:$OASIS_RABBIT_PORT" -t 60
./src/utils/wait-for-it.sh "$OASIS_CELERY_DB_HOST:$OASIS_CELERY_DB_PORT" -t 60

# Start worker on init
celery worker -A src.model_execution_worker.tasks --loglevel=INFO -Q "${OASIS_MODEL_SUPPLIER_ID}-${OASIS_MODEL_ID}-${OASIS_MODEL_VERSION_ID}" |& tee -a /var/log/oasis/worker.log
