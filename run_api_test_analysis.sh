#!/bin/bash

oasislmf test model-api
python oasisapi_client/model_api_tester.py http://oasis_api_server -a tests/data/analysis_settings.json -i tests/data/input -o tests/data/output
