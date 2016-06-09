#!/bin/bash

# Start worker on init
celery worker --detach --config=common.CeleryConfig --loglevel=INFO --logfile="/var/log/oasis/%n.log"