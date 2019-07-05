#!/bin/bash

export OASIS_MODEL_DATA_DIR=<..path to piwind ..>

docker rmi coreoasis/api_server:latest
docker rmi coreoasis/model_worker:latest

docker build -f Dockerfile.api_server -t coreoasis/api_server .
docker build -f Dockerfile.model_worker -t coreoasis/model_worker .
docker-compose up -d
