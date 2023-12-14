#!/bin/sh
# This file adds/updates oasis with the model set in environment variables.
#
# Model settings are read from model_settings.json in the model data volume.
#
# Script compatible with sh and not bash

set -x 
set -e
set -o pipefail

BASE_URL="http://${OASIS_SERVER_HOST}:${OASIS_SERVER_PORT}/api"
MODEL_SETTINGS_FILE="$OASIS_MODEL_DATA_DIRECTORY/model_settings.json"
CHUNKING_CONFIGURATION_FILE="$OASIS_MODEL_DATA_DIRECTORY/chunking_configuration.json"
SCALING_CONFIGURATION_FILE="$OASIS_MODEL_DATA_DIRECTORY/scaling_configuration.json"

echo
echo "=== Register model ==="
echo "API version      : $OASIS_API_VERSION"
echo "Supplier ID      : $OASIS_MODEL_SUPPLIER_ID"
echo "Model ID         : $OASIS_MODEL_ID"
echo "Model version ID : $OASIS_MODEL_VERSION_ID"
echo "Model path       : $OASIS_MODEL_DATA_DIRECTORY"
echo "Model groups     : $OASIS_MODEL_GROUPS"
echo

if [ -z "$OASIS_MODEL_SUPPLIER_ID" ] || [ -z "$OASIS_MODEL_ID" ] || [ -z "$OASIS_MODEL_VERSION_ID" ] || [ -z "$OASIS_MODEL_DATA_DIRECTORY" ] || [ -z "$OASIS_API_VERSION" ]; then
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
  -d "{ \"username\": \"${OASIS_ADMIN_USER}\", \"password\": \"${OASIS_ADMIN_PASS}\"}" | jq -r '.access_token // empty')

if [ -n "$ACCESS_TOKEN" ]; then
  echo "Authenticated"
else
  echo "Failed to authenticate:"
  curl -X POST "${BASE_URL}/access_token/" -H "accept: application/json" -H "Content-Type: application/json" \
    -d "{ \"username\": \"${OASIS_ADMIN_USER}\", \"password\": \"${OASIS_ADMIN_PASS}\"}"
  exit 1
fi

curlf() {
  OUTPUT_FILE=$(mktemp)
  HTTP_CODE=$(curl --silent --output "$OUTPUT_FILE" --write-out "%{http_code}" -H "Authorization: Bearer ${ACCESS_TOKEN}" "$@")
  if [[ ${HTTP_CODE} -lt 200 || ${HTTP_CODE} -gt 299 ]]; then
    >&2 echo "Http code: ${HTTP_CODE}"
    >&2 cat "$OUTPUT_FILE"
    rm -f "$OUTPUT_FILE"
    return 22
  fi
  cat "$OUTPUT_FILE"
  rm -f "$OUTPUT_FILE"
}

MODEL_ID=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X GET \
  "${BASE_URL}/v1/models/?supplier_id=${OASIS_MODEL_SUPPLIER_ID}&version_id=${OASIS_MODEL_VERSION_ID}" | \
  jq ".[] | select((.supplier_id | ascii_downcase == \"$(echo ${OASIS_MODEL_SUPPLIER_ID} | \
  tr '[:upper:]' '[:lower:]')\") and (.model_id | ascii_downcase == \"$(echo ${OASIS_MODEL_ID} | \
  tr '[:upper:]' '[:lower:]')\") and (.version_id == \"$(echo ${OASIS_MODEL_VERSION_ID} | tr '[:upper:]' '[:lower:]')\")) | .id")

MODEL_JSON_ID_ATTRIBUTES="\"supplier_id\": \"${OASIS_MODEL_SUPPLIER_ID}\",\"model_id\": \"${OASIS_MODEL_ID}\",\"version_id\": \"${OASIS_MODEL_VERSION_ID}\""

if [ -n "$MODEL_ID" ]; then
  echo "Model exists with id $MODEL_ID"
else
  echo "Model not found - registers it"

  MODEL_ID=$(curlf -X POST "${BASE_URL}/${OASIS_API_VERSION}/models/" -H "Content-Type: application/json" \
    -d "{${MODEL_JSON_ID_ATTRIBUTES}"} | jq .id)
  echo "Created with id $MODEL_ID"

fi

echo "Set model groups"
GROUPS_JSON="{${MODEL_JSON_ID_ATTRIBUTES}, \"groups\": []}"
if [ -n "$OASIS_MODEL_GROUPS" ]; then

  GROUPS_JSON="{${MODEL_JSON_ID_ATTRIBUTES}, \"groups\": [\"$(echo $OASIS_MODEL_GROUPS | sed 's/,/","/g')\"]}"
fi
curlf -X PATCH "${BASE_URL}/${OASIS_API_VERSION}/models/${MODEL_ID}/" -H "Content-Type: application/json" -d "$GROUPS_JSON" | jq .

echo "Uploading model settings"
curlf -X POST "${BASE_URL}/${OASIS_API_VERSION}/models/${MODEL_ID}/settings/" -H "Content-Type: application/json" -d @${MODEL_SETTINGS_FILE} | jq .

if [[ "$OASIS_API_VERSION" == "v2" ]]; then 
    if [ -f "$CHUNKING_CONFIGURATION_FILE" ]; then
      echo "Uploading chunking configuration"
      curlf -X POST "${BASE_URL}/${OASIS_API_VERSION}/models/${MODEL_ID}/chunking_configuration/" -H "Content-Type: application/json" -d @${CHUNKING_CONFIGURATION_FILE} | jq .
    fi

    if [ -f "$SCALING_CONFIGURATION_FILE" ]; then
      echo "Uploading scaling configuration"
      curlf -X POST "${BASE_URL}/${OASIS_API_VERSION}/models/${MODEL_ID}/scaling_configuration/" -H "Content-Type: application/json" -d @${SCALING_CONFIGURATION_FILE} | jq .
    fi
fi 

echo "Finished"
