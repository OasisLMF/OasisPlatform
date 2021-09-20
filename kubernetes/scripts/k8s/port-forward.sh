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

allThreads=(
"deployment/oasis-server 8000:8000"
"deployment/oasis-ui 8080:3838"
"deployment/monitoring-grafana 3000:3000"
"statefulset/prometheus-monitoring-kube-prometheus-prometheus 9090"
"statefulset/alertmanager-monitoring-kube-prometheus-alertmanager 9093:9093"
"deployment/server-db 5432"
)

for host in "${allThreads[@]}"; do
  echo $host
  kubectl port-forward $host &
  pids="$pids $!"
done

# wait for all pids
for pid in ${pids[*]}; do
    wait $pid
done
