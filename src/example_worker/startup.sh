#!/bin/bash

# Start worker on init
celery worker --detach --config=CeleryConfig -l DEBUG \
    --pidfile="/home/worker/%n.pid" \
    --logfile="/home/worker/%n.log"