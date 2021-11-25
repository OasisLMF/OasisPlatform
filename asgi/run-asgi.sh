#!/usr/bin/env bash
daphne -b 0.0.0.0 -p 8000 --root-path /api src.server.oasisapi.asgi:application
