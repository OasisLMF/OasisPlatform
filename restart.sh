#!/bin/bash

docker-compose down
docker build -t oasis_api_server -f Dockerfile.oasis_api_server .
docker build -t model_execution_worker -f Dockerfile.model_execution_worker .
docker build -t api_runner -f Dockerfile.api_runner .
docker-compose up -d
