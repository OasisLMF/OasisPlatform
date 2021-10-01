#!/bin/bash

set -e

SCRIP_DIR=$(dirname $0)

echo "ls -lt /mnt/host/; rm -rf /mnt/host/*; echo deleted; ls -lt /mnt/host/" | $SCRIP_DIR/host_volume_shell.sh
