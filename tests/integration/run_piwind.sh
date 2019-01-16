#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPT_DIR

# Resolve IP of API
API_IP=$(getent hosts oasisplatform_server_1 | awk '{ print $1 }') && echo $API_IP


# Register Piwind Model 
oasislmf api add-model -u http://$API_IP:8000 -l admin_auth.json --model-id PiWind --version-id 1 --supplier-id OasisIM

# Check Model added to DB
oasislmf api list      -u http://$API_IP:8000 -l admin_auth.json -m

# Run Model 
oasislmf api run       -u http://$API_IP:8000 -l admin_auth.json -x piwind/SourceLocOEDPiWind10.csv -j piwind/analysis_settings.json -m 1
