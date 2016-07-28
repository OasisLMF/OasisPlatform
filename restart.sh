#!/bin/bash

docker-compose down
docker build -t my_server -f Dockerfile.server .
docker build -t model_execution_worker -f Dockerfile.model_execution_worker .
docker-compose up -d
