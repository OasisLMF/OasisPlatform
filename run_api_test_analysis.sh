#!/bin/bash

python src/utils/api_tester.py -i localhost:8001 -a tests/data/analysis_settings.json -d tests/data/input -o tests/data/output

