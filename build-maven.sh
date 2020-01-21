#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Set 'pom.xml' version tag: used to locate the swagger schema api
if [ -z "$1" ]; then 
    echo "Missing version tag: './build-maven.sh <API-ReleaseTag>'"
    exit 1
else    
    VERSION_TAG=$1
    echo "Testing version: $VERSION_TAG"
fi 


if [ -z "$2" ]; then
    DOCKER_TAG='latest'
else
    DOCKER_TAG=$1
fi


docker build -f docker/Dockerfile.mvn-build -t mvn-tester .
docker run -v $SCRIPT_DIR:/home/build mvn-tester:$DOCKER_TAG $VERSION_TAG
