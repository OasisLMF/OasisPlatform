#!/bin/bash
docker run --rm -v $PWD:/spec redocly/cli build-docs analysis_settings_schema.json --options='{"hideDownloadButton": true}'
