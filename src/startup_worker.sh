#!/bin/bash
set -e

# Install packages from a specific version
if [ ! -z "${OASIS_OASISLMF_VERSION}" ] ; then
  echo "Overwriting oasislmf version";
  pip uninstall oasislmf -y || true
  pip install --no-cache-dir --user --no-warn-script-location oasislmf==${OASIS_OASISLMF_VERSION}
fi

version_valid() {
    python3 -c "
import sys
from importlib.metadata import distribution
from packaging.requirements import Requirement
from packaging.version import Version
dist = distribution('oasislmf')

for req_str in dist.requires:
    req = Requirement(req_str)
    if req.name == sys.argv[1]:
        if Version(sys.argv[2]) in req.specifier:
            sys.exit(0)
        sys.exit(1)
 " "$1" "$2"
}

if [ ! -z "${OASIS_ODS_VERSION}" ] ; then
  if version_valid "ods-tools" ${OASIS_ODS_VERSION} ; then
    echo "Overwriting ods version";
    pip uninstall ods-tools -y || true
    pip install --no-cache-dir --user --no-warn-script-location ods-tools==${OASIS_ODS_VERSION}
  else
    echo "Invalid version of ODS"
    exit 1
  fi
fi

if [ ! -z "${OASIS_ODM_VERSION}" ] ; then
  if version_valid "oasis-data-manager" ${OASIS_ODM_VERSION} ; then
    echo "Overwriting odm version";
    pip uninstall oasis-data-manager -y || true
    pip install --no-cache-dir --user --no-warn-script-location oasis-data-manager==${OASIS_ODM_VERSION}
  else
    echo "Invalid version of ODM"
    exit 1
  fi
fi

# The image's numba cache (jit-warmup stage) is compiled with none of OASIS_INT / OASIS_FLOAT /
# OASIS_AREAPERIL_TYPE set, i.e. oasislmf's defaults. The dtypes are built into the compiled code and
# aren't part of numba's cache key, so a worker that sets any of them could load mismatched code
# (segfaults, bad results). Clear it so the pytools compile with this worker's dtypes on first use.
# Checks for any value rather than comparing with the defaults, so it doesn't depend on oasislmf's.
if [ -n "${OASIS_INT}${OASIS_FLOAT}${OASIS_AREAPERIL_TYPE}" ]; then
  echo "oasislmf dtypes set (OASIS_INT=${OASIS_INT} OASIS_FLOAT=${OASIS_FLOAT} OASIS_AREAPERIL_TYPE=${OASIS_AREAPERIL_TYPE}): clearing the prebuilt numba cache"
  oasislmf clearcache || echo "WARNING: 'oasislmf clearcache' failed, the prebuilt numba cache may not match these dtypes"
fi

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
SELECT_RUN_MODE=$(echo "$OASIS_RUN_MODE" | tr '[:upper:]' '[:lower:]')
case "$SELECT_RUN_MODE" in
    "v1")
      API_VER=''
      TASK_FILE='src.model_execution_worker.tasks'
    ;;
    "v2")
      API_VER='-v2'
      TASK_FILE='src.model_execution_worker.distributed_tasks'
    ;;
    "server-internal")
      API_VER=''
      OASIS_MODEL_SUPPLIER_ID='oasis'
      OASIS_MODEL_ID='internal'
      OASIS_MODEL_VERSION_ID='worker'
      TASK_FILE='src.model_execution_worker.server_tasks'
    ;;
    *)
        echo "Invalid value for api version:"
        echo " Set 'OASIS_RUN_MODE=v1'  For Single server execution"
        echo " Set 'OASIS_RUN_MODE=v2'  For Distributed execution"
        exit 1
    ;;
esac

# Start new worker on init
celery --app $TASK_FILE worker $WORKER_CONCURRENCY --loglevel=INFO -Q "${OASIS_MODEL_SUPPLIER_ID}-${OASIS_MODEL_ID}-${OASIS_MODEL_VERSION_ID}${API_VER}" ${OASIS_CELERY_EXTRA_ARGS} |& tee -a /var/log/oasis/worker.log
