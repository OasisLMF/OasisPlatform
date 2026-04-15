#!/usr/bin/env bash
# Generate self-signed certificates for RabbitMQ AMQPS (development only).
# Run this once before starting the AMQPS broker:
#   bash compose/rabbitmq-ssl/gen-certs.sh
set -euo pipefail

CERTS_DIR="$(cd "$(dirname "$0")" && pwd)/certs"
mkdir -p "$CERTS_DIR"

openssl req -x509 -newkey rsa:4096 \
    -keyout  "$CERTS_DIR/server_key.pem" \
    -out     "$CERTS_DIR/server_certificate.pem" \
    -days 365 -nodes \
    -subj '/CN=broker' \
    -addext "subjectAltName=DNS:broker,DNS:localhost,IP:127.0.0.1"

# Use the server cert as its own CA (self-signed)
cp "$CERTS_DIR/server_certificate.pem" "$CERTS_DIR/ca_certificate.pem"

# Ensure the rabbitmq container user can read the files
chmod 644 "$CERTS_DIR/server_key.pem" "$CERTS_DIR/server_certificate.pem" "$CERTS_DIR/ca_certificate.pem"

echo "Certificates written to $CERTS_DIR"
