#!/bin/bash

# Delete celeryd.pid file - fix que pickup issues on reboot of server
rm -f /home/worker/celeryd.pid


# Start worker on init
celery worker -A model_execution_worker.tasks --loglevel=INFO --logfile="/dev/stdout" -Q %CELERY_QUEUE%
