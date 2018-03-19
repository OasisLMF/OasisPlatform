#!/usr/bin/python
import sys
import logging

sys.path.insert(0, '/var/www/oasis/')

from conf.settings import settings

logging.basicConfig(stream=sys.stdout)
settings.setup_logging('server')


from server import APP as application
application.secret_key = settings.get('server', 'SECRET_KEY')
