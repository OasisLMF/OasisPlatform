#!/bin/bash

set -e

migrate_from_ver=(
    '2.1.1'
#    '2.1.1'
#    '2.1.0'
    '1.28.0'
    '1.27.5'
    '1.26.8'
    '1.23.18'
    '1.15.29'
)

for ver in "${migrate_from_ver[@]}"
do
    echo --- Testing $ver ---
    rm -f src/server/db.sqlite3 
    git co $ver && ./manage.py migrate && git co fix/migrations-plat1-to-plat2 && ./manage.py migrate
done

