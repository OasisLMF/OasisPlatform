#!/usr/bin/env bash
#daphne -b 0.0.0.0 -p 8001 --root-path /api src.server.oasisapi.asgi:application
daphne -b 0.0.0.0 -p 8001 src.server.oasisapi.asgi:application
