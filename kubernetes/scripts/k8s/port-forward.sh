#!/bin/bash

pids=""

function cleanup()
{
    echo "trap $pids"
    kill $pids
    ps $pids
}

trap cleanup EXIT

kubectl port-forward deployment/oasis-server 8000:8000 &
pids="$pids $!"
kubectl port-forward deployment/oasis-ui 8080:3838 &
pids="$pids $!"
kubectl port-forward deployment/monitoring-grafana 3000:3000 &
pids="$pids $!"
kubectl port-forward statefulset/prometheus-monitoring-kube-prometheus-prometheus 9090 &
pids="$pids $!"

# wait for all pids
for pid in ${pids[*]}; do
    wait $pid
done
