#!/bin/bash

pids=""

function cleanup()
{
    if [ -n "$pids" ]; then
      echo "trap $pids"
      kill $pids
      ps $pids
    fi
}

trap cleanup EXIT

forwards=()

for arg in "${@}"; do
  case $arg in
  "api")
    forwards+=("deployment/oasis-server 8001:8000")
    ;;
  "ui")
    forwards+=("deployment/oasis-ui 8080:3838")
    ;;
  "db")
    forwards+=("deployment/server-db 5432")
    forwards+=("deployment/celery-db 5431:5432")
    forwards+=("deployment/broker 6379")
    ;;
  "keycloak")
    forwards+=("deployment/keycloak 8081:8080")
    ;;
  "monitoring")
    forwards+=("deployment/monitoring-grafana 3000:3000")
    forwards+=("statefulset/prometheus-monitoring-kube-prometheus-prometheus 9090")
    forwards+=("statefulset/alertmanager-monitoring-kube-prometheus-alertmanager 9093:9093")
    ;;
  "all"|"")
    exec @0 db api ui keycloak monitoring
    ;;
  esac

done

for fw in "${forwards[@]}"; do
  echo $fw
  kubectl port-forward $fw &
  pids="$pids $!"
done

# wait for all pids
for pid in ${pids[*]}; do
    wait $pid
done
