#!/bin/bash
chmod a+w /var/oasis/upload
chmod a+w /var/oasis/download

# Start worker on init
celery worker -A model_execution_worker.tasks --detach --config=common.CeleryConfig --loglevel=INFO --logfile="/var/log/oasis/celery_worker.log"