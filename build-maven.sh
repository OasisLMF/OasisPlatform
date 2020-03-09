#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VERSION_TAG='1.1'
DOCKER_TAG='latest'

docker build -f docker/Dockerfile.mvn-build -t mvn-tester .
# Set 'pom.xml' version tag: used to locate the swagger schema api
if [ ! -z "$1" ]; then 
    VERSION_TAG=$1
fi 

echo "Testing version: $VERSION_TAG"
docker run -v $SCRIPT_DIR:/home/build mvn-tester:$DOCKER_TAG $VERSION_TAG
