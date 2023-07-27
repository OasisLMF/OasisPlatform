#python3 bipython3 bash

# This is a help script to fix migration confits between Platform 2 
# Needed for versions older than 2.2.0 migrating to to any version above 2.2.1+ 
# 
# For details see: https://github.com/OasisLMF/OasisPlatform/pull/862

# Revert analysis_models
python3 manage.py migrate analysis_models 0004_analysismodel_deleted
python3 manage.py migrate analysis_models  --fake

# Revert analyses 
python3 manage.py migrate analyses 0010_auto_20200224_1213
python3 manage.py migrate analyses --fake

# Revert data_files
python3 manage.py migrate data_files 0006_datafile_file_category
python3 manage.py migrate data_files --fake

# Revert files
python3 manage.py migrate files 0005_relatedfile_oed_validated
python3 manage.py migrate files --fake 

# Revert portfolios
python3 manage.py migrate portfolios 0002_auto_20190619_1226
python3 manage.py migrate portfolios --fake 

# ReRun Migrations 
python3 manage.py migrate
