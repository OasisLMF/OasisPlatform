#!/bin/sh
# wait-for-server.sh

host="$1"
shift
cmd="$@"



SERVER_HEALTH=0
until [ $SERVER_HEALTH -gt 0 ] ; do
  >&2 echo "Server is unavailable - sleeping"
  sleep 1
  echo "curl -X GET 'http://$host/healthcheck/'"
  SERVER_HEALTH=$(curl -s -X GET "http://$host/healthcheck/" -H "accept: application/json" | grep -c "OK")
done

>&2 echo "Server is up - executing command: " 
echo $cmd
exec $cmd
