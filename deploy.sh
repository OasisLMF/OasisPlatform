#!/bin/bash

export OASIS_MODEL_DATA_DIR=<piwind path>
COMPOSE_FILE='docker-compose.yml'

if [ $(docker volume ls | grep OasisData -c) -gt 1 ]; then
    docker-compose -f $COMPOSE_FILE down
    printf "Deleting docker data: \n"
    docker volume ls | grep OasisData | awk 'BEGIN { FS = "[ \t\n]+" }{ print $2 }' | xargs -r docker volume rm
    docker rmi coreoasis/api_server:dev
    docker rmi coreoasis/model_worker:dev
fi

docker build -f Dockerfile.api_server -t coreoasis/api_server:dev .
docker build -f Dockerfile.model_worker -t coreoasis/model_worker:dev .
docker-compose -f $COMPOSE_FILE up -d
