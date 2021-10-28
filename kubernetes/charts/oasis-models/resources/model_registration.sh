#!/bin/sh
# This file adds/updates oasis with the model set in environment variables.
#
# Model settings are read from model_settings.json in the model data volume.
#
# Script compatible with sh and not bash

set -e

BASE_URL="http://${OASIS_SERVER_HOST}:${OASIS_SERVER_PORT}"
MODEL_SETTINGS_FILE="$OASIS_MODEL_DATA_DIRECTORY/model_settings.json"
CHUNKING_CONFIGURATION_FILE="$OASIS_MODEL_DATA_DIRECTORY/chunking_configuration.json"
SCALING_CONFIGURATION_FILE="$OASIS_MODEL_DATA_DIRECTORY/scaling_configuration.json"

echo
echo "=== Register model ==="
echo "Supplier ID      : $OASIS_MODEL_SUPPLIER_ID"
echo "Model ID         : $OASIS_MODEL_ID"
echo "Model version ID : $OASIS_MODEL_VERSION_ID"
echo "Model path       : $OASIS_MODEL_DATA_DIRECTORY"
echo

if [ -z "$OASIS_MODEL_SUPPLIER_ID" ] || [ -z "$OASIS_MODEL_ID" ] || [ -z "$OASIS_MODEL_VERSION_ID" ] || [ -z "$OASIS_MODEL_DATA_DIRECTORY" ]; then
  echo "Missing required model env var(s)"
  exit 1
fi

if [ ! -f "$MODEL_SETTINGS_FILE" ]; then
  echo "No $MODEL_SETTINGS_FILE found in model path"
  exit 1
fi

if [ -z "$OASIS_SERVER_HOST" ] || [ -z "$OASIS_SERVER_PORT" ]; then
  echo "Missing required API env var(s)"
  exit 1
fi

if [ -z "$OASIS_ADMIN_USER" ] || [ -z "$OASIS_ADMIN_PASS" ]; then
  echo "Missing required API credentials env var(s)"
  exit 1
fi


ACCESS_TOKEN=$(curl -s -X POST "${BASE_URL}/access_token/" -H "accept: application/json" -H "Content-Type: application/json" \
  -d "{ \"username\": \"${OASIS_ADMIN_USER}\", \"password\": \"${OASIS_ADMIN_PASS}\"}" | jq -r .access_token)

if [ -n "$ACCESS_TOKEN" ]; then
  echo "Authenticated"
else
  echo "Failed to authenticate"
  exit 1
fi

MODEL_ID=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X GET \
  "${BASE_URL}/v1/models/?supplier_id=${OASIS_MODEL_SUPPLIER_ID}&version_id=${OASIS_MODEL_VERSION_ID}" | \
  jq ".[] | select((.supplier_id | ascii_downcase == \"$(echo ${OASIS_MODEL_SUPPLIER_ID} | \
  tr '[:upper:]' '[:lower:]')\") and (.model_id | ascii_downcase == \"$(echo ${OASIS_MODEL_ID} | \
  tr '[:upper:]' '[:lower:]')\") and (.version_id == \"$(echo ${OASIS_MODEL_VERSION_ID} | tr '[:upper:]' '[:lower:]')\")) | .id")

if [ -n "$MODEL_ID" ]; then
  echo "Model exists with id $MODEL_ID"
else
  echo "Model not found - registers it"

  MODEL_ID=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X POST "${BASE_URL}/v1/models/" -H "Content-Type: application/json" \
    -d "{\"supplier_id\": \"${OASIS_MODEL_SUPPLIER_ID}\",\"model_id\": \"${OASIS_MODEL_ID}\",\"version_id\": \"${OASIS_MODEL_VERSION_ID}\""} | jq .id)
  echo "Created with id $MODEL_ID"

fi

echo "Uploading model settings"
curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X POST "${BASE_URL}/v1/models/${MODEL_ID}/settings/" -H "Content-Type: application/json" -d @${MODEL_SETTINGS_FILE} | jq .

if [ -f "$CHUNKING_CONFIGURATION_FILE" ]; then
  echo "Uploading chunking configuration"
  curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X POST "${BASE_URL}/v1/models/${MODEL_ID}/chunking_configuration/" -H "Content-Type: application/json" -d @${CHUNKING_CONFIGURATION_FILE} | jq .
fi

if [ -f "$SCALING_CONFIGURATION_FILE" ]; then
  echo "Uploading scaling configuration"
  curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X POST "${BASE_URL}/v1/models/${MODEL_ID}/scaling_configuration/" -H "Content-Type: application/json" -d @${SCALING_CONFIGURATION_FILE} | jq .
fi

echo "Finished"

fi
