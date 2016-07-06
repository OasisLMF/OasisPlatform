#!/bin/bash

docker-compose down
docker build -t my_server -f Dockerfile.server .
docker build -t my_worker -f Dockerfile.model_execution_worker .
docker-compose up -d