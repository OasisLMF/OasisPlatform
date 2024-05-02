#!/bin/bash


SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PIWIND_PATH_FILE=$SCRIPT_DIR/piwind-path-cfg
cd $SCRIPT_DIR; cd ..
pwd

# Store PiWind Path
if ! [ -f $PIWIND_PATH_FILE ]; then
    touch $PIWIND_PATH_FILE
else
    source $PIWIND_PATH_FILE
fi

if [[ -z $OASIS_MODEL_DATA_DIR ]]; then
    echo -n "OasisPiwind Repo Path: "
    read filepath
        if [ ! -d $filepath ]; then
            echo "Please insert a correct path"
            sleep 1
            $SCRIPT_DIR/deploy.sh
        fi
    export OASIS_MODEL_DATA_DIR=$filepath
    echo "export OASIS_MODEL_DATA_DIR=$filepath" > $PIWIND_PATH_FILE
fi

#docker rmi coreoasis/api_server:dev
#docker rmi coreoasis/model_worker:dev

# Check for prev install and offer to clean wipe
if [[ $(docker volume ls | grep OasisData -c) -gt 1 ]]; then
    printf "Deleting docker data: \n"
    docker volume ls | grep OasisData | awk 'BEGIN { FS = "[ \t\n]+" }{ print $2 }' | xargs -r docker volume rm
fi


# Install Oasis-Data-Manager from git branch (Optional) 'docker build --build-arg odm_branch=develop'
# Install ODS-Tools from git branch (Optional) 'docker build --build-arg ods_tools_branch=develop'
# Install MDK from git branch (Optional) 'docker build --build-arg oasislmf_branch=develop'

ODM_BRANCH=''
ODS_BRANCH=''
LMF_BRANCH=''

BUILD_ARGS_WORKER=''
BUILD_ARGS_SERVER=''
if [ ! -z $ODM_BRANCH ]; then
    BUILD_ARGS_WORKER="${BUILD_ARGS_WORKER} --build-arg odm_branch=${ODM_BRANCH}"
    BUILD_ARGS_SERVER="${BUILD_ARGS_SERVER} --build-arg odm_branch=${ODM_BRANCH}"
fi

if [ ! -z $ODS_BRANCH ]; then
    BUILD_ARGS_WORKER="${BUILD_ARGS_WORKER} --build-arg ods_tools_branch=${ODS_BRANCH}"
    BUILD_ARGS_SERVER="${BUILD_ARGS_SERVER} --build-arg ods_tools_branch=${ODS_BRANCH}"
fi

if [ ! -z $LMF_BRANCH ]; then
    BUILD_ARGS_WORKER="${BUILD_ARGS_WORKER} --build-arg oasislmf_branch=${LMF_BRANCH}"
fi

set -e
docker build -f Dockerfile.api_server $BUILD_ARGS_SERVER -t coreoasis/api_server:dev .
docker build -f Dockerfile.model_worker $BUILD_ARGS_WORKER -t coreoasis/model_worker:dev .
# docker-compose -f compose/s3.docker-compose.yml up -d
docker-compose -f up -d
