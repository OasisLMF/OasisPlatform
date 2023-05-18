#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export PYTHONPATH=$SCRIPT_DIR

# Set the ini file path
export OASIS_INI_PATH="${SCRIPT_DIR}/conf.ini"

# Delete celeryd.pid file - fix que pickup issues on reboot of server
rm -f /home/worker/celeryd.pid


# ---- needs to be one or the other?? ---
    # OLD - wait for it (test and remove)
    #./src/utils/wait-for-it.sh "$OASIS_RABBIT_HOST:$OASIS_RABBIT_PORT" -t 60
    # use for REDIS
    ./src/utils/wait-for-it.sh "$OASIS_CELERY_BROKER_URL" -t 60

./src/utils/wait-for-it.sh "$OASIS_CELERY_DB_HOST:$OASIS_CELERY_DB_PORT" -t 60

# Start current worker on init
# celery --app src.model_execution_worker.tasks worker --concurrency=1 --loglevel=INFO -Q "${OASIS_MODEL_SUPPLIER_ID}-${OASIS_MODEL_ID}-${OASIS_MODEL_VERSION_ID}" |& tee -a /var/log/oasis/worker.log


# set concurrency flag
if [ -z "$OASIS_CELERY_CONCURRENCY" ]
then
      WORKER_CONCURRENCY=''
else
      WORKER_CONCURRENCY='--concurrency '$OASIS_CELERY_CONCURRENCY
fi

# Start new worker on init
celery --app src.model_execution_worker.distributed_tasks worker $WORKER_CONCURRENCY --loglevel=INFO -Q "${OASIS_MODEL_SUPPLIER_ID}-${OASIS_MODEL_ID}-${OASIS_MODEL_VERSION_ID}" ${OASIS_CELERY_EXTRA_ARGS} |& tee -a /var/log/oasis/worker.log
