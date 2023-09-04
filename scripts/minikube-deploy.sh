#!/bin/bash

# cd to repo root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPT_DIR/..

# Store PiWind Path
if [[ -z $OASIS_MODEL_DATA_DIR ]]; then
    echo -n "OasisPiwind Repo Path: "
    read filepath
        if [ ! -d $filepath ]; then
            echo "Please insert a correct path"
            sleep 1
            $SCRIPT_DIR/deploy.sh
        fi
    export OASIS_MODEL_DATA_DIR=$filepath
fi

# Wipe minikube
#minikube delete


# build images
eval $(minikube docker-env)
set -e
    docker build -f Dockerfile.api_server -t coreoasis/api_server:dev .
    docker build -f Dockerfile.model_worker -t coreoasis/model_worker:dev .

    pushd kubernetes/worker-controller
        docker build -t coreoasis/worker_controller:dev .
    popd
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
