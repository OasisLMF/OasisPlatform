#!/bin/sh
# wait-for-server.sh

host="$1"
shift
cmd="$@"

SERVER_HEALTH=0
echo "curl -X GET 'http://$host/healthcheck/'"

until [ $SERVER_HEALTH -gt 0 ] ; do
  SERVER_HEALTH=$(curl -s -X GET "http://$host/healthcheck/" -H "accept: application/json" | grep -c "OK")

  if [ "$SERVER_HEALTH" -lt 1 ]; then
      >&1 echo "Waiting for server"
      sleep 2
  fi 
done

>&2 echo "Server is up - executing command: " 
echo $cmd
exec $cmd
