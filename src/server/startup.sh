#!/bin/bash
chmod a+w /var/www/oasis/upload
chmod a+w /var/www/oasis/download
chmod a+w /var/log/oasis

apachectl start
