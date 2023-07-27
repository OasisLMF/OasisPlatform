#!/bin/bash

# This is a help script to fix migration confits between Platform versions older than 2.2.0
# to any version above 2.2.1+ 
# For details see: https://github.com/OasisLMF/OasisPlatform/pull/862

# Revert analysis_models
./manage.py migrate analysis_models 0004_analysismodel_deleted
./manage.py migrate analysis_models  --fake

# Revert analyses 
./manage.py migrate analyses 0010_auto_20200224_1213
./manage.py migrate analyses --fake

# Revert data_files
./manage.py migrate data_files 0006_datafile_file_category
./manage.py migrate data_files --fake

# Revert files
./manage.py migrate files 0005_relatedfile_oed_validated
./manage.py migrate files --fake 

# Revert portfolios
./manage.py migrate portfolios 0002_auto_20190619_1226
./manage.py migrate portfolios --fake 

# ReRun Migrations 
./manage.py migrate
