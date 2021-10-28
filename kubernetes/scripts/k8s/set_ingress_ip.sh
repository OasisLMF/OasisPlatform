#!/bin/bash

IP="$(kubectl get svc --template="{{range .items}}{{range .status.loadBalancer.ingress}}{{.ip}}{{end}}{{end}}")"

echo "Found IP: $IP"

if ! echo "$IP" | egrep -q '^([0-9]{1,3}[.]){1,}[0-9]{1,3}$'; then
  echo "No external IP found"
  exit
fi

set -e

cp /etc/hosts /tmp/hosts
sudo sed -i "s/^[0-9.]*\([\t ]*[a-z]*.oasis.local\)/${IP}\1/" /etc/hosts
diff /etc/hosts /tmp/hosts
