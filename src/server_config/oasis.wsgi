#!/usr/bin/python
import sys
import logging

from src.conf.settings import settings

logging.basicConfig(stream=sys.stderr)
settings.setup_logging('server')

sys.path.insert(0, '/var/www/oasis/')

from server import APP as application
application.secret_key = settings.get('server', 'SECRET_KEY')
