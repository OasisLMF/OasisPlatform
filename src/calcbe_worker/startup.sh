#!/bin/bash
chmod a+w /var/www/oasis/upload
chmod a+w /var/www/oasis/download

# Start worker on init
celery worker --detach --config=common.CeleryConfig --loglevel=INFO --logfile="/var/log/oasis/%n.log"