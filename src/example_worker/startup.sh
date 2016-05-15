#!/bin/bash

# Start worker on init
celery worker --detach --config=CeleryConfig -l DEBUG \
    --pidfile="/home/example_worker/%n.pid" \
    --logfile="/home/example_worker/%n.log"