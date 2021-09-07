#!/bin/sh

set -e

MAX_TRIES=30

echo "Grafana host : $GRAFANA_HOST"
echo "Grafana user : $GRAFANA_USER"
echo "Grafana pass : $(if [ -n "$GRAFANA_PASSWORD" ]; then echo "****"; fi)"
echo "Dashboard uid: $DASHBOARD_UID"

if [ -z "$GRAFANA_USER" ] || [ -z "$GRAFANA_PASSWORD" ] || [ -z "$DASHBOARD_UID" ]; then
  echo "Missing required env var"
  exit 1
fi

apk --quiet add curl jq

echo -n "Waiting for Grafana."
n=0
until [ "$n" -ge $MAX_TRIES ]
do
  if curl -s http://${GRAFANA_HOST}/healthz | grep -q "Ok"; then
    break
  fi
  echo -n "."
  n=$((n+1))
  sleep 2
done

if [ "$n" == "$MAX_TRIES" ]; then
  echo "Can't reach Grafana"
  exit 1
else
  echo
fi

HDID=$(curl -s http://${GRAFANA_USER}:${GRAFANA_PASSWORD}@${GRAFANA_HOST}/api/user/preferences | jq .homeDashboardId)
if [ "$HDID" == "0" ]; then
  echo "Default dashboard found - set custom"
  echo -n "Looking for graph."

  n=0
  until [ "$n" -ge $MAX_TRIES ]
  do
    ID=$(curl -s "http://${GRAFANA_USER}:${GRAFANA_PASSWORD}@${GRAFANA_HOST}/api/dashboards/uid/$DASHBOARD_UID" | jq '.dashboard.id//empty')
    if [ -n "$ID" ]; then
      echo
      echo "Dashboard $DASHBOARD_UID found with id $ID"
      curl -s -X PUT -H "Content-Type: application/json" -d "{\"homeDashboardId\":$ID}" \
        http://${GRAFANA_USER}:${GRAFANA_PASSWORD}@${GRAFANA_HOST}/api/user/preferences
        exit
    fi

    echo -n "."
    n=$((n+1))
    sleep 2
  done

  echo
  echo "Dashboard $DASHBOARD_UID not found"
  exit 1

else
  echo "Custom dashboard already set"
fi
