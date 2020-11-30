#!/usr/bin/env bash
IMAGE_NAME=$1
REPORT_NAME=$2

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_OUTPUT=$SCRIPT_DIR/$REPORT_NAME
mkdir -p $(dirname $LOG_OUTPUT)

set -e 
docker run -v /var/run/docker.sock:/var/run/docker.sock wagoodman/dive --ci $IMAGE_NAME | tee $LOG_OUTPUT
