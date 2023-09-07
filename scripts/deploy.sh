#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPT_DIR; cd ..
pwd


if [[ -z $OASIS_MODEL_DATA_DIR ]]; then
    echo -n "Path: "
    read filepath
        if [ ! -d $filepath ]; then
            echo "Please insert a correct path"
            sleep 1
            $SCRIPT_DIR/deploy.sh
        fi
    export OASIS_MODEL_DATA_DIR=$filepath    
fi

docker rmi coreoasis/api_server:dev
docker rmi coreoasis/model_worker:dev

# Check for prev install and offer to clean wipe
if [[ $(docker volume ls | grep OasisData -c) -gt 1 ]]; then
    printf "Deleting docker data: \n"
    docker volume ls | grep OasisData | awk 'BEGIN { FS = "[ \t\n]+" }{ print $2 }' | xargs -r docker volume rm
fi

docker build -f Dockerfile.api_server -t coreoasis/api_server:dev .
docker build -f Dockerfile.model_worker -t coreoasis/model_worker:dev .
docker-compose up -d
