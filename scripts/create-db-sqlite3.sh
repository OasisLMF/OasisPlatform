#!/bin/bash

set -e 
function usage {
    echo "Usage: $0 <OasisPlatform Tag>,  e.g. 2.3.10, or 1.28.9"
    echo
    echo " This script initializes an db.sqlite3 DB file, used for testing migration changes added to the platform."
}

if [ -z "$1" ]; then
    usage
    exit 1
else
    SERVER_TAG=$1
fi

SERVER_IMAGE='coreoasis/api_server'
SQL_FILE='src/server/oasisapi/db.sqlite3'
ENTRY='/usr/bin/python3'
CMD='manage.py migrate'
#CMD='/bin/bash'

if [ -f $SQL_FILE ]; then
    echo "Found existing file $SQL_FILE - deleting and creating a empty file"
    rm -f $SQL_FILE
fi
touch $SQL_FILE
chmod 777 $SQL_FILE


echo "Creating a blank db.sqlite3 file for OasisPlatform $SERVER_TAG"
echo 
docker run -e OASIS_SERVER_DB_ENGINE=django.db.backends.sqlite3 --entrypoint $ENTRY -v ./$SQL_FILE:/var/www/oasis/$SQL_FILE $SERVER_IMAGE:$SERVER_TAG $CMD
echo "-- Done --"
