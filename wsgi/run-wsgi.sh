#!/usr/bin/env bash

# Gateway Config options
# https://docs.gunicorn.org/en/stable/settings.html

BIND_ADDR='0.0.0.0:8000'
WORKERS=$(python3 -c "import os; print(len(os.sched_getaffinity(0)))" 2>/dev/null)
WORKERS=${WORKERS:-1}
TIMEOUT=600
LOG_LEVEL='info'

export GUNICORN_CMD_ARGS="--bind=$BIND_ADDR --workers=$WORKERS --timeout $TIMEOUT --log-level=$LOG_LEVEL"
gunicorn src.server.oasisapi.wsgi
