#!/bin/bash

set -eux
python manage.py makemigrations
python manage.py migrate

export OASIS_MODEL_DATA_DIR=/home/sam/repos/models/piwind

docker build -f Dockerfile.oasis_api_server.base  -t coreoasis/oasis_api_base .
docker build -f Dockerfile.oasis_api_server.mysql -t coreoasis/oasis_api_server .
docker build -f Dockerfile.model_execution_worker -t coreoasis/model_execution_worker .

#docker-compose up -d
