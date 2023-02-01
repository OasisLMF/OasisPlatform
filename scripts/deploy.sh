#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPT_DIR; cd ..
pwd


if [[ -z $OASIS_MODEL_DATA_DIR ]]; then 
   echo '"OASIS_MODEL_DATA_DIR" not set, searching for PiWind in home dir:'
   mapfile -d $'\0' options < <(find ~/ -type d -path "*/model_data/PiWind" -print0 2> /dev/null)


   PS3="$prompt "
   select opt in "${options[@]}" "Quit" ; do 
     if (( REPLY == 1 + "${#options[@]}" )) ; then
       exit
     elif (( REPLY > 0 && REPLY <= "${#options[@]}" )) ; then
       echo  "You picked $opt which is file $REPLY"
       export OASIS_MODEL_DATA_DIR=$opt
       break
     else
       echo "Invalid option. Try another one."
     fi
   done

fi     

docker rmi coreoasis/api_server:latest
docker rmi coreoasis/model_worker:latest

docker build -f Dockerfile.api_server -t coreoasis/api_server .
docker build -f Dockerfile.model_worker -t coreoasis/model_worker .
docker-compose up -d
