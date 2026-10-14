#!/usr/bin/python3
# Python, not bash, as the api_server image has no shell. The '.sh' name is kept so the
# existing compose / helm commands ("./wsgi/run-wsgi.sh") keep working.

# Gateway Config options
# https://docs.gunicorn.org/en/stable/settings.html
import os

BIND_ADDR = '0.0.0.0:8000'
WORKERS = len(os.sched_getaffinity(0)) or 1
TIMEOUT = 600
LOG_LEVEL = 'info'

os.environ['GUNICORN_CMD_ARGS'] = f'--bind={BIND_ADDR} --workers={WORKERS} --timeout {TIMEOUT} --log-level={LOG_LEVEL}'
os.execvp('gunicorn', ['gunicorn', 'src.server.oasisapi.wsgi'])
