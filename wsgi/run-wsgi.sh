#!/usr/bin/env bash

# Gateway Config options
# https://docs.gunicorn.org/en/stable/settings.html

BIND_ADDR='0.0.0.0:8000'
WORKERS=$(nproc --all)
TIMEOUT=600
LOG_LEVEL='info'

export GUNICORN_CMD_ARGS="--bind=$BIND_ADDR --workers=$WORKERS --timeout $TIMEOUT --log-level=$LOG_LEVEL"
gunicorn src.server.oasisapi.wsgi
