#!/bin/bash

export OASIS_MODEL_DATA_DIR=<..path to piwind ..>

docker rmi coreoasis/api_server:dev
docker rmi coreoasis/model_worker:dev

docker build -f Dockerfile.api_server -t coreoasis/api_server:dev .
docker build -f Dockerfile.model_worker -t coreoasis/model_worker:dev .
docker-compose up -d
