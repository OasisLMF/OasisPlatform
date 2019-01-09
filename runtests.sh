#!/usr/bin/env bash

CWD=$(pwd)
LOG_OUTPUT=$CWD/reports
TAR_OUTPUT=$CWD/dist

mkdir $LOG_OUTPUT $TAR_OUTPUT

if [ -z "$1" ]; then
    DOCKER_TAG='latest'
else
    DOCKER_TAG=$1
fi

docker build -f docker/Dockerfile.oasisplatform_tester -t oasisplatform-tester .
docker run -v $LOG_OUTPUT:/var/log/oasis -v $TAR_OUTPUT:/tmp/output oasisplatform-tester:$DOCKER_TAG
