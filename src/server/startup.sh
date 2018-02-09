#!/bin/bash
set -e

chmod a+w /var/www/oasis/upload
chmod a+w /var/www/oasis/download
chown -R www-data:www-data /var/www/oasis/upload
chown -R www-data:www-data /var/www/oasis/download

# apachectl -k start -DFOREGROUND
apachectl start
