#!/usr/bin/python3
# Python, not bash, as the api_server image has no shell. The '.sh' name is kept so the
# existing compose / helm commands ("./asgi/run-asgi.sh") keep working.
import os

# os.execvp('daphne', ['daphne', '-b', '0.0.0.0', '-p', '8001', '--root-path', '/api', 'src.server.oasisapi.asgi:application'])
os.execvp('daphne', ['daphne', '-b', '0.0.0.0', '-p', '8001', 'src.server.oasisapi.asgi:application'])
