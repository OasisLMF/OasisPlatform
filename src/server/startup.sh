#!/bin/bash
chmod a+w /var/www/oasis/upload
chmod a+w /var/www/oasis/download
chown -R worker:worker /var/www/oasis/upload
chown -R worker:worker /var/www/oasis/download

apachectl start -DFOREGROUND
