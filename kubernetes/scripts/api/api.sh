#!/bin/bash

set -e

CMD=$1
ANALYSIS_ID=$2

function usage() {
  echo "Usage: $0 [ls|generate|execute|run] <analysis id>"
  exit 0
}

function join {
  local IFS="$1"
  shift
  echo "$*"
}


if [ -z "$CMD" ]; then
  usage
fi

source $(dirname $0)/common.sh

case $CMD in
  "ls")
    case "$ANALYSIS_ID" in
      "p"|"portfolio"|"portfolios")
        curlf -X GET "${API_URL}/v2/portfolios/" | jq -r '.[] | "\(.id) - \(.name)\r\t\t\t\tgroups: \(.groups | join (","))"' | sort -n
      ;;
      "m"|"model"|"models")
        curlf -X GET "${API_URL}/v2/models/" | jq -r '.[] | "\(.id) - \(.supplier_id)-\(.model_id)-\(.version_id)\r\t\t\t\tgroups: \(.groups | join (","))"' | sort -n
      ;;
      "df"|"data-files"|"datafiles")
        curlf -X GET "${API_URL}/v2/data_files/" | jq -r '.[] | "\(.id) - \(.filename)\r\t\t\t\tgroups: \(.groups | join (","))"'| sort -n
      ;;
      *)
        curlf -X GET "${API_URL}/v2/analyses/" | jq -r '.[] | "\(.id) - \(.status) - \(.name)\r\t\t\t\t\t\tportfolio: \(.portfolio)\tmodel: \(.model)\tgroups: \(.groups | join (","))"' | sort -n
      ;;
    esac
  ;;
  "create")

    NAME=$3
    PGROUPS=$4
    if [ -z "$NAME" ]; then
      echo "$0 ${@} <name> [groups]"
      exit
    fi

    PARAMS=()

    if [ -n "$PGROUPS" ]; then
      PARAMS+=("\"groups\":[\"$(echo $PGROUPS | sed 's/,/","/g')\"]")
    fi

    case "$2" in
      "m"|"model")
        PARAMS+=("\"supplier_id\": \"jxn\"")
        PARAMS+=("\"model_id\": \"jxn_catastrophy\"")
        PARAMS+=("\"version_id\": \"${NAME}\"")
        curlf -X POST "${API_URL}/v1/models/" -H  "Content-Type: application/json" -d "{$(join , "${PARAMS[@]}")}" | jq .
      ;;
      "portfolio")
        PARAMS+=("\"name\": \"${NAME}\"")
        curlf -X POST "${API_URL}/v1/portfolios/" -H  "Content-Type: application/json" -d "{$(join , "${PARAMS[@]}")}" | jq .
      ;;
      "df")
        PARAMS+=("\"file_description\": \"${NAME}\"")
        R=$($CURL -H "$CAH" -X POST "${API_URL}/v1/data_files/" -H  "Content-Type: application/json" -d "{$(join , "${PARAMS[@]}")}")
        DFID=$(echo $R | jq -r '.id // empty' || true)
        if [ -z "$DFID" ]; then
          echo "Failed to create data file: $R"
          exit 1
        fi
        echo "Data file created with id: $DFID"
        echo "" | curlf -X POST "${API_URL}/v1/data_files/${DFID}/content/" -H  "Content-Type: multipart/form-data" -F "file=@-;filename=${NAME};type=application/json" | jq .
      ;;
    esac
  ;;
  "rm"|"remove"|"delete")

    IDS="${@:3}"
    if [ -z "$IDS" ]; then
      echo "$0 ${@} <id>"
      exit
    fi

    for id in $IDS; do
      echo -n "Removes $id: "

      case "$2" in
        "df")
          curlf -X DELETE -s -o /dev/null -w "%{http_code}" "${API_URL}/v1/data_files/${id}/"
        ;;
        "portfolio"|"p")
          curlf -X DELETE -s -o /dev/null -w "%{http_code}" "${API_URL}/v1/portfolios/${id}/"
        ;;
        "analysis"|"a")
          curlf -X DELETE -s -o /dev/null -w "%{http_code}" "${API_URL}/v1/analyses/${id}/"
        ;;
      esac

      echo

    done
  ;;
  "cancel"|"stop")
    if [ -z "$ANALYSIS_ID" ]; then
      usage
    fi

    curlf -X POST "${API_URL}/v1/analyses/${ANALYSIS_ID}/cancel/" | jq -r '.status'
  ;;
  "generate"|"input")
    if [ -z "$ANALYSIS_ID" ]; then
      usage
    fi

    curlf -X POST "${API_URL}/v1/analyses/${ANALYSIS_ID}/generate_inputs/" | jq -r '.status'
  ;;
  "execute"|"loss")
    if [ -z "$ANALYSIS_ID" ]; then
      usage
    fi

    curlf -X POST "${API_URL}/v1/analyses/${ANALYSIS_ID}/run/" | jq -r '.status'
  ;;
  "run")

    if [ -z "$ANALYSIS_ID" ]; then
      usage
    fi

    if [ "${#@}" == 2 ]; then

      echo "$ANALYSIS_ID: $($0 input $ANALYSIS_ID) - input start"

      while :; do
        STATUS=$($CURL -H "$CAH" -X GET "${API_URL}/v1/analyses/${ANALYSIS_ID}/" | jq -r '.status')
        echo "$ANALYSIS_ID: $STATUS"

        if [ $STATUS == "READY" ]; then
          echo "$ANALYSIS_ID: $($0 loss $ANALYSIS_ID) - loss start"
        elif [ $STATUS == "RUN_COMPLETED" ] || [ $STATUS == "INPUTS_GENERATION_ERROR" ] || [ $STATUS == "RUN_ERROR" ]; then
          break
        fi

        sleep 2
      done

    else

      PS=()
      function cleanup()
      {
          echo "${PS[@]}"
          kill "${PS[@]}"
          exit
      }

      trap cleanup SIGINT

      for i in "${@:2}"; do
        $0 run $i &
        PS+=($!)
      done

      wait
    fi
  ;;
  "queue-status"|"qs")
    curlf -X GET "${API_URL}/v1/queue-status/" | jq .
  ;;
  "token")
    echo $ACCESS_TOKEN
  ;;
  "claim")
    echo $ACCESS_TOKEN | egrep -o "[.].**$" | sed 's/^.//' | base64 -d | jq .
  ;;
  *)
    usage
esac
