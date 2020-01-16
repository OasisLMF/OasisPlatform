#!/bin/bash

host=server:8000
SERVER_HEALTH=0
echo "curl -s -X GET 'http://$host/healthcheck/'"

until [ $SERVER_HEALTH -gt 0 ] ; do
  SERVER_HEALTH=$(curl -s -X GET "http://$host/healthcheck/" -H "accept: application/json" | grep -c "OK")

  if [ "$SERVER_HEALTH" -lt 1 ]; then 
      >&2 echo "Waiting for Server"
      sleep 2
  fi 
done

echo "Server is available - exit"
set -e

if [ -z "${TEST_TIMEOUT}" ]; then
    TEST_TIMEOUT=180
fi     

timeout $TEST_TIMEOUT pytest -v -p no:django /home/worker/tests/integration/api_integration.py "$@"
