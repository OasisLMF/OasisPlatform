#!/bin/bash

DIR_OUTPUT='/var/oasis/test/output'
RUN_LOG='run_output.log'
TIMEOUT=120


timeout $TIMEOUT oasislmf test model-api http://oasis_api_server -a tests/integration/analysis_settings.json \
                                                                 -i tests/integration/input/csv \
                                                                 -o $DIR_OUTPUT | tee $RUN_LOG

ERROR_CHECK=$(cat $RUN_LOG | grep -ci error)
EXCEPTION_CHECK=$(cat $RUN_LOG | grep -ci exception)
if [ $ERROR_CHECK -ne 0 ] || [ $EXCEPTION_CHECK -ne 0 ]; then
    echo "Error Detected"
    exit 1
fi

COMPLETE_CHECK=$(cat $RUN_LOG | grep -ci 'Finished: 1 completed, 0 failed')
if [ $COMPLETE_CHECK -ne 1 ]; then 
    echo "Execution timed out at '${TIMEOUT}' seconds"
    exit 1
fi  
