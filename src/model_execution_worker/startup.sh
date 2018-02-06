#!/bin/bash

# Delete celeryd.pid file - fix que pickup issues on reboot of server
rm -f /home/worker/celeryd.pid


# Start worker on init
celery worker -A model_execution_worker.tasks --detach --loglevel=INFO --logfile="/var/log/oasis/worker.log" -Q %CELERY_QUEUE%
