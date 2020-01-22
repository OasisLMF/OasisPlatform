#!/bin/bash
set -e 
MVN_LOG='reports/mvm-build.log'

# set version tag 
    cp /tmp/pom.xml ./
    #if [[ -z "${1// }" ]]; then 
    #    sed -i "s|RELEASE_TAG|$1|g" pom.xml
    #    sed -i 's|SCHEMA_FILE|openapi-schema-${project.version}.json|g' pom.xml
    #else 
    #    sed -i "s|RELEASE_TAG|1.1|g" pom.xml
    #    sed -i 's|SCHEMA_FILE|openapi-schema.json|g' pom.xml
    #fi

    sed -i "s|RELEASE_TAG|$1|g" pom.xml
    sed -i 's|SCHEMA_FILE|reports/openapi-schema.json|g' pom.xml

# run build
    mvn package | tee $MVN_LOG
    mvn test | tee $MVN_LOG

# Check output 
set +exu
MVN_PASS=$(cat $MVN_LOG | grep -ci 'BUILD SUCCESS')
if [ $MVN_PASS -ne 1 ]; then 
    echo "Marven build test - FAILED"
    exit 1
else
    echo "Marven build test - PASSED"
    exit 0
fi 
