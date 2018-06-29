#!/usr/bin/env bash

uwsgi --ini ${UWSGI_CONF:-./uwsgi/uwsgi.ini}
