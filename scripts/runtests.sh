#!/usr/bin/env bash

LOG_OUTPUT=$SCRIPT_DIR/reports
TAR_OUTPUT=$SCRIPT_DIR/dist
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPT_DIR; cd ..

mkdir $LOG_OUTPUT $TAR_OUTPUT

if [ -z "$1" ]; then
    DOCKER_TAG='latest'
else
    DOCKER_TAG=$1
fi


docker build -f docker/Dockerfile.oasisplatform_tester -t oasisplatform-tester .
docker run -v $LOG_OUTPUT:/var/log/oasis -v $TAR_OUTPUT:/tmp/output oasisplatform-tester:$DOCKER_TAG
