#!/bin/bash

# This is a help script to fix migration confits between Platform 2 
# Needed for versions older than 2.2.0 migrating to to any version above 2.2.1+ 
# 
# For details see: https://github.com/OasisLMF/OasisPlatform/pull/862

# Revert analysis_models
python3 manage.py migrate analysis_models 0004_analysismodel_deleted
python3 manage.py migrate analysis_models 0007_modelscalingoptions_worker_count_min  --fake

# Revert analyses 
python3 manage.py migrate analyses 0010_auto_20200224_1213
python3 manage.py migrate analyses 0011_auto_20230724_1134 --fake

# Revert data_files
python3 manage.py migrate data_files 0006_datafile_file_category
python3 manage.py migrate data_files 0007_auto_20230724_1134 --fake

# Revert files
python3 manage.py migrate files 0005_relatedfile_oed_validated
python3 manage.py migrate files 0006_relatedfile_groups --fake 

# Revert portfolios
python3 manage.py migrate portfolios 0002_auto_20190619_1226
python3 manage.py migrate portfolios 0003_auto_20230724_1134 --fake 

# ReRun Migrations 
python3 manage.py migrate
