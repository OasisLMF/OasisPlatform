#!/bin/sh
# This file will check available models in environment variables and register/update each one
# by calling model_registration.sh.
#
# Script compatible with sh and not bash

set -e

PATH_SPACE_SUBSTITUTE="#"
SCRIPT_DIR="$(dirname $0)"

echo "Add curl and jq"
apk add curl jq

counter=0
while true; do

  if [ -n "$(sh -c "echo \$OASIS_MODEL_SUPPLIER_ID_${counter}")" ]; then

    export OASIS_MODEL_SUPPLIER_ID="$(sh -c "echo \$OASIS_MODEL_SUPPLIER_ID_${counter}")"
    export OASIS_MODEL_ID="$(sh -c "echo \$OASIS_MODEL_ID_${counter}")"
    export OASIS_MODEL_VERSION_ID="$(sh -c "echo \$OASIS_MODEL_VERSION_ID_${counter}")"
    export OASIS_MODEL_DATA_DIRECTORY="$(sh -c "echo \$OASIS_MODEL_DATA_DIRECTORY_${counter}")"

    ${SCRIPT_DIR}/model_registration.sh
  else
    break
  fi

  counter=$(expr $counter + 1)

done
