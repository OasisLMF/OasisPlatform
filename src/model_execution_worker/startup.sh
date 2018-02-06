#!/bin/bash
set -ex

# Delete celeryd.pid file - fix que pickup issues on reboot of server
rm -f /home/worker/celeryd.pid

sed -i -e "s/%RABBIT_PORT%/$RABBIT_PORT/" /home/worker/common/CeleryConfig.py
sed -i -e "s/%MYSQL_PORT%/$MYSQL_PORT/" /home/worker/common/CeleryConfig.py
sed -i -e "s/%CELERY_QUEUE%/$MODEL_SUPPLIER_ID-$MODEL_VERSION_ID/" startup.sh

./utils/wait-for-it.sh "oasis_rabbit:$RABBIT_PORT"
./utils/wait-for-it.sh "oasis_mysql:$MYSQL_PORT"

chmod a+w /var/www/oasis/upload
chmod a+w /var/www/oasis/download
chown -R oasis:www-data /var/www/oasis/upload
chown -R oasis:www-data /var/www/oasis/download


# Start worker on init
celery worker -A model_execution_worker.tasks --detach --loglevel=INFO --logfile="/var/log/oasis/worker.log" -Q %CELERY_QUEUE%

tail -f /var/log/oasis/worker.log
