#!/bin/bash

pip install -r /var/www/oasis/oasisapi_client/requirements.txt
pip install -r /var/www/oasis/model_execution_worker/requirements.txt

python oasisapi_client/model_api_tester.py -s http://oasis_api_server -a tests/data/analysis_settings.json -i tests/data/input -o tests/data/output
