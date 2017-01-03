#!/bin/bash

# Start worker on init
celery worker -A model_execution_worker.tasks --detach --loglevel=INFO --logfile="/var/log/oasis/worker.log"