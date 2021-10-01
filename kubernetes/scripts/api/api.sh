#!/bin/bash

set -e

OASIS_USER=$1
OASIS_PASSWORD=$2
CMD=$3
ANALYSIS_ID=$4

function usage() {
  echo "Usage: $0 <oasisuser> <password> [ls|generate|execute|run] <analysis id>"
  exit 0
}

if [ -z "$CMD" ]; then
  usage
fi

source $(dirname $0)/common.sh

case $CMD in
  "ls")
    curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X GET "${BASE_URL}/v1/analyses/" | jq -r '.[] | "\(.id) - \(.status) - \(.name)"'
  ;;
  "cancel")
    if [ -z "$ANALYSIS_ID" ]; then
      usage
    fi

    curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X POST "${BASE_URL}/v1/analyses/${ANALYSIS_ID}/cancel/" | jq -r '.status[0]'
  ;;
  "generate")
    if [ -z "$ANALYSIS_ID" ]; then
      usage
    fi

    curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X POST "${BASE_URL}/v1/analyses/${ANALYSIS_ID}/generate_inputs/" | jq -r '.status'
  ;;
  "execute")
    if [ -z "$ANALYSIS_ID" ]; then
      usage
    fi

    curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X POST "${BASE_URL}/v1/analyses/${ANALYSIS_ID}/run/" | jq -r '.status'
  ;;
  "run")
    if [ -z "$ANALYSIS_ID" ]; then
      usage
    fi

    $0 $OASIS_USER $OASIS_PASSWORD generate $ANALYSIS_ID

    while :; do
      STATUS=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X GET "${BASE_URL}/v1/analyses/${ANALYSIS_ID}/" | jq -r '.status')
      echo $STATUS

      if [ $STATUS == "READY" ]; then
        $0 $OASIS_USER $OASIS_PASSWORD execute $ANALYSIS_ID
      elif [ $STATUS == "RUN_COMPLETED" ]; then
        break
      fi

      sleep 2
    done
  ;;
  *)
    usage
esac
