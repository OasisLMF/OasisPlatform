#!/bin/bash
chmod a+w /var/www/oasis/upload
chmod a+w /var/www/oasis/download
chown -R oasis:oasis /var/www/oasis/upload
chown -R oasis:oasis /var/www/oasis/download

apachectl -k start -DFOREGROUND
