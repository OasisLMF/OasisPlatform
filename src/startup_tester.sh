#!/bin/bash
set -e

TIMEOUT=180
timeout $TIMEOUT pytest -v -p no:django /home/worker/tests/integration/api_integration.py "$@"
