#!/bin/bash

python src/oasisapi_client/model_api_tester.py -s http://localhost:8001 -a tests/data/analysis_settings.json -i tests/data/input -o tests/data/output

