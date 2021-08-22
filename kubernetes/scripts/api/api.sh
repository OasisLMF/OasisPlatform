#!/bin/bash

set -e

CMD=$1
ANALYSIS_ID=$2

function usage() {
  echo "Usage: $0 [ls|generate|execute|run] <analysis id>"
  exit 0
}

if [ -z "$CMD" ]; then
  usage
fi

source $(dirname $0)/common.sh

case $CMD in
  "ls")
    $CURL -H "$CAH" -X GET "${API_URL}/v1/analyses/" | jq -r '.[] | "\(.id) - \(.status) - \(.name)"'
  ;;
  "cancel"|"stop")
    if [ -z "$ANALYSIS_ID" ]; then
      usage
    fi

    $CURL -H "$CAH" -X POST "${API_URL}/v1/analyses/${ANALYSIS_ID}/cancel/" | jq -r '.status[0]'
  ;;
  "generate")
    if [ -z "$ANALYSIS_ID" ]; then
      usage
    fi

    $CURL -H "$CAH" -X POST "${API_URL}/v1/analyses/${ANALYSIS_ID}/generate_inputs/" | jq -r '.status'
  ;;
  "execute")
    if [ -z "$ANALYSIS_ID" ]; then
      usage
    fi

    $CURL -H "$CAH" -X POST "${API_URL}/v1/analyses/${ANALYSIS_ID}/run/" | jq -r '.status'
  ;;
  "run")

    if [ -z "$ANALYSIS_ID" ]; then
      usage
    fi

    $0 generate $ANALYSIS_ID

    while :; do
      STATUS=$($CURL -H "$CAH" -X GET "${API_URL}/v1/analyses/${ANALYSIS_ID}/" | jq -r '.status')
      echo $STATUS

      if [ $STATUS == "READY" ]; then
        $0 execute $ANALYSIS_ID
      elif [ $STATUS == "RUN_COMPLETED" ]; then
        break
      fi

      sleep 2
    done
  ;;
  "queue-status"|"qs")
    $CURL -H "$CAH" -X GET "${API_URL}/v1/queue-status/" | jq .
  ;;
  *)
    usage
esac
