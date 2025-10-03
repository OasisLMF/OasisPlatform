#!/bin/bash

set -e 

# cd to repo root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PIWIND_PATH_FILE=$SCRIPT_DIR/piwind-path-cfg
cd $SCRIPT_DIR/..

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

## init minikube
# minikube delete
# minikube config set cpus 12
# minikube config set memory 16000
# minikube start

# build images

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

eval $(minikube docker-env)
set -e
    docker build -f Dockerfile.api_server $BUILD_ARGS_SERVER -t coreoasis/api_server:dev .
    docker build -f Dockerfile.model_worker $BUILD_ARGS_WORKER -t coreoasis/model_worker:dev .

    pushd kubernetes/worker-controller
        docker build -t coreoasis/worker_controller:dev .
    popd
    docker build -f ../OasisUI/docker/Dockerfile.oasisui_development -t coreoasis/oasisui_dev:dev ../OasisUI
set +e

# Upload piwind data
./kubernetes/scripts/k8s/upload_piwind_model_data.sh $OASIS_MODEL_DATA_DIR

# update / apply charts
pushd kubernetes/charts
    if ! helm status platform; then
        helm install platform oasis-platform
    else
        helm upgrade platform oasis-platform
    fi

    if ! helm status models; then
        helm install models oasis-models
    else
        helm upgrade models oasis-models
    fi
popd

# kubectl scale --replicas=0 deployment/oasis-worker-controller

# Open local access to cluster
#
#minikube tunnel &
# kubectl get svc --template="{{range .items}}{{range .status.loadBalancer.ingress}}{{.ip}}{{end}}{{end}}"

# Open single service
#kubectl port-forward deployment/oasis-websocket 8001:8001  #(forward websocket)
