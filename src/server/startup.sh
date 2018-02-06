#!/bin/bash
chmod a+w /var/www/oasis/upload
chmod a+w /var/www/oasis/download
chown -R oasis:www-data /var/www/oasis/upload
chown -R oasis:www-data /var/www/oasis/download

# apachectl -k start -DFOREGROUND
apachectl
