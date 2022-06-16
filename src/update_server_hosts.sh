#!/bin/bash
set -e

# Keycloak is bound to a specific hostname which requires us to use the same url to query keycloak in backend that is
# used in the UI for authentication (the JWT will contain the authenticaiton URL). We can't access the external ingress
# hostname but we can map it in the hosts file to point to the ingress service.
if [ -n "$INGRESS_EXTERNAL_HOST" ] && [ -n "$INGRESS_INTERNAL_HOST" ]; then
  INGRESS_SERVICE_IP="$(getent hosts "$INGRESS_INTERNAL_HOST" | awk '{ print $1 }')"
  if [ -n "$INGRESS_SERVICE_IP" ]; then
    echo "$(getent hosts "$INGRESS_INTERNAL_HOST" | awk '{ print $1 }') ${INGRESS_EXTERNAL_HOST}" >> /etc/hosts
    echo "Ingress external hostname $INGRESS_EXTERNAL_HOST is now set to ip $INGRESS_SERVICE_IP"
    echo "/etc/hosts:"
    cat /etc/hosts
  else
    echo "Could not resolve IP for service: $INGRESS_INTERNAL_HOST"
    exit 1
  fi
fi
