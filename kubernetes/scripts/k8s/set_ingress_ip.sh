#!/bin/bash

set -e

IP="$(kubectl get svc --template="{{range .items}}{{range .status.loadBalancer.ingress}}{{.ip}}{{end}}{{end}}")"

echo "Found IP: $IP"

if ! echo "$IP" | grep -qE '^([0-9]{1,3}[.]){1,}[0-9]{1,3}$'; then
  echo "No external IP found"
  exit
fi

if grep -qE ".*${IP}.*ui.oasis.local" /etc/hosts; then
  echo "No update needed"
  exit
fi

BF="/tmp/hosts.$(date +%s)"
cp /etc/hosts $BF
echo "Hosts file backuped as $BF"

if ! grep -q .oasis.local /etc/hosts; then
  echo "Adding ui.oasis.local to hosts file:"
  cat << EOF | sudo tee -a /etc/hosts

# Oasis Kubernetes cluster hostname
$IP ui.oasis.local

EOF
else
  echo "Host already exists in hosts file, updating it..."
  sudo sed -i "s/^[0-9.]*\([\t ]*[a-z]*.oasis.local\)/${IP}\1/" /etc/hosts
fi

echo "Diff between /etc/hosts $BF:"
diff /etc/hosts $BF

