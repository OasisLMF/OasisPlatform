#!/bin/bash
set -e 
MVN_LOG='reports/mvm-build.log'

# set version tag 
    cp /tmp/pom.xml ./
    sed -i "s|RELEASE_TAG|$1|g" pom.xml

# run build
    mvn install | tee $MVN_LOG

# Check output 
set +exu
MVN_FAILED=$(cat $MVN_LOG | grep -ci 'BUILD FAILURE')
if [ $MVN_FAILED -ne 0 ]; then 
    echo "Marven build test - FAILED"
    exit 1
else
    echo "Marven build test - PASSED"
    exit 0
fi 
