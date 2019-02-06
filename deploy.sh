#!/bin/bash

#export OASIS_MODEL_DATA_DIR=<..path to piwind ..>

docker build -f Dockerfile.oasis_api_server.base  -t coreoasis/oasis_api_base .
docker build -f Dockerfile.oasis_api_server.mysql -t coreoasis/oasis_api_server .
docker build -f Dockerfile.model_execution_worker -t coreoasis/model_execution_worker .
docker-compose up -d
