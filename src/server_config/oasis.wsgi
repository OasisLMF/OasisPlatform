#!/usr/bin/python
import sys
import logging
logging.basicConfig(stream=sys.stdout)
sys.path.insert(0,"/var/www/oasis/")

from server import APP as application
application.secret_key = 'Add your secret key'
