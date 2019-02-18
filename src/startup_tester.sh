#!/bin/bash



host=server:8000

SERVER_HEALTH=0
until [ $SERVER_HEALTH -gt 0 ] ; do
  >&2 echo "Server is unavailable - sleeping"
  echo "curl -s -X GET 'http://$host/healthcheck/'"
  SERVER_HEALTH=$(curl -s -X GET "http://$host/healthcheck/" -H "accept: application/json" | grep -c "OK")
  sleep 5
done
echo "Server is available - exit"
sleep 10
set -e
TIMEOUT=180
timeout $TIMEOUT pytest -v -p no:django /home/worker/tests/integration/api_integration.py "$@"
