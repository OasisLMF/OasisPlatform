#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export PYTHONPATH=$SCRIPT_DIR

# Set the ini file path
export OASIS_INI_PATH="${SCRIPT_DIR}/conf.ini"


# Delete celeryd.pid file - fix que pickup issues on reboot of server
rm -f /home/worker/celeryd.pid


# Check connectivity
./src/utils/wait-for-it.sh "$OASIS_CELERY_BROKER_URL" -t 60
./src/utils/wait-for-it.sh "$OASIS_CELERY_DB_HOST:$OASIS_CELERY_DB_PORT" -t 60


# set concurrency flag
if [ -z "$OASIS_CELERY_CONCURRENCY" ]
then
      WORKER_CONCURRENCY=''
else
      WORKER_CONCURRENCY='--concurrency '$OASIS_CELERY_CONCURRENCY
fi


# Oasis select API version
SELECT_API_VERSION=$(echo "$OASIS_API_VERSION" | tr '[:upper:]' '[:lower:]')
case "$SELECT_API_VERSION" in
    "v1")
      API_VER=''
      TASK_FILE='src.model_execution_worker.tasks'
    ;;
    "v2")
      API_VER='-v2'
      TASK_FILE='src.model_execution_worker.distributed_tasks'
    ;;
    *)
        echo "Invalid value for api version:"
        echo " Set 'OASIS_API_VERSION=v1'  For Single server execution"
        echo " Set 'OASIS_API_VERSION=v2'  For Distributed execution"
        exit 1
    ;;
esac


# Start new worker on init
celery --app $TASK_FILE worker $WORKER_CONCURRENCY --loglevel=INFO -Q "${OASIS_MODEL_SUPPLIER_ID}-${OASIS_MODEL_ID}-${OASIS_MODEL_VERSION_ID}${API_VER}" ${OASIS_CELERY_EXTRA_ARGS} |& tee -a /var/log/oasis/worker.log
