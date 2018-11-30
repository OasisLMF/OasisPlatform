#!/bin/bash

set -eux
python manage.py makemigrations
python manage.py migrate

docker build -f Dockerfile.oasis_api_server.base -t oasis_api_server:base .
docker build -f Dockerfile.oasis_api_server.mysql -t oasis_api_server:mysql .
docker build -f Dockerfile.model_execution_worker -t model_execution_worker .

docker-compose up -d
