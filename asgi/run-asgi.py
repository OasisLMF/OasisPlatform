#!/usr/bin/python3
import os

# os.execvp('daphne', ['daphne', '-b', '0.0.0.0', '-p', '8001', '--root-path', '/api', 'src.server.oasisapi.asgi:application'])
os.execvp('daphne', ['daphne', '-b', '0.0.0.0', '-p', '8001', 'src.server.oasisapi.asgi:application'])
