#!/bin/bash

#
# Creates a reference folder structures for ktools model execution and calcBE
#

#
# Set the root directory
#
cd .

#
# Make the top level directories
#

# To hold all model data
mkdir model_repository
# To hold all exposure uploads 
mkdir upload
# To hold outputs ready for download
mkdir download
# Analysis working directory
mkdir analysis

#
# Populate a model
#

# Supplier
mkdir model_repository/OASIS
# Model
mkdir model_repository/OASIS/PiWind
# Version
mkdir model_repository/OASIS/PiWind/1.0
# Event sets
mkdir model_repository/OASIS/PiWind/1.0/eventset1
mkdir model_repository/OASIS/PiWind/1.0/eventset1/occurrence1
mkdir model_repository/OASIS/PiWind/1.0/eventset1/occurrence2
mkdir model_repository/OASIS/PiWind/1.0/eventset2
mkdir model_repository/OASIS/PiWind/1.0/eventset2/occurrence1
mkdir model_repository/OASIS/PiWind/1.0/eventset2/occurrence2
# Model data files
touch model_repository/OASIS/PiWind/1.0/eventfootprint.bin
touch model_repository/OASIS/PiWind/1.0/eventfootprint.idx
touch model_repository/OASIS/PiWind/1.0/damage_bin_dict.bin
touch model_repository/OASIS/PiWind/1.0/vulnerability.bin
touch model_repository/OASIS/PiWind/1.0/eventset1/events.bin
touch model_repository/OASIS/PiWind/1.0/eventset1/occurrence1/occurrence.bin
touch model_repository/OASIS/PiWind/1.0/eventset1/occurrence2/occurrence.bin
touch model_repository/OASIS/PiWind/1.0/eventset2/events.bin
touch model_repository/OASIS/PiWind/1.0/eventset2/occurrence1/occurrence.bin
touch model_repository/OASIS/PiWind/1.0/eventset2/occurrence2/occurrence.bin

#
# Uploads
#
touch upload/coverages.bin
touch upload/fm_policytc.bin
touch upload/fm_programme.bin
touch upload/fmsummaryxref.bin
touch upload/items.bin
touch upload/events.bin
touch upload/fm_profile.bin
touch upload/fm_xref.bin
touch upload/gulsummaryxref.bin
touch upload/returnperiod.bin

cd upload
tar czvf 25892e17-80f6-415f-9c65-7395632f0223.tar.gz \
    coverages.bin fm_policytc.bin fm_programme.bin \
    fmsummaryxref.bin items.bin events.bin fm_profile.bin \
    fm_xref.bin gulsummaryxref.bin  returnperiod.bin
rm *.bin
cd -

#
# When running an analysis...
#

# Create analysis specific working directory
mkdir analysis/a53e98e4-0197-4513-be6d-49836e406aaa
mkdir analysis/a53e98e4-0197-4513-be6d-49836e406aaa/input
mkdir analysis/a53e98e4-0197-4513-be6d-49836e406aaa/output
mkdir analysis/a53e98e4-0197-4513-be6d-49836e406aaa/work

# Link or copy in the required data files
ln -s "$(pwd)/model_repository/OASIS/PiWind/1.0/" analysis/a53e98e4-0197-4513-be6d-49836e406aaa/static
ln -s "$(pwd)/model_repository/OASIS/PiWind/1.0/eventset1/events.bin" analysis/a53e98e4-0197-4513-be6d-49836e406aaa/input/
ln -s "$(pwd)model_repository/OASIS/PiWind/1.0/eventset1/occurrence1/occurrence.bin" analysis/a53e98e4-0197-4513-be6d-49836e406aaa/input/

# Extract the exposure files
tar xzf upload/25892e17-80f6-415f-9c65-7395632f0223.tar.gz --directory analysis/a53e98e4-0197-4513-be6d-49836e406aaa/input

# Run the analysis...
touch analysis/a53e98e4-0197-4513-be6d-49836e406aaa/output/gul_0_elt.csv
touch analysis/a53e98e4-0197-4513-be6d-49836e406aaa/output/gul_0_full_uncertainty_aep.csv
touch analysis/a53e98e4-0197-4513-be6d-49836e406aaa/output/gul_0_full_uncertainty_oep.csv
touch analysis/a53e98e4-0197-4513-be6d-49836e406aaa/output/il_0_elt.csv
touch analysis/a53e98e4-0197-4513-be6d-49836e406aaa/output/il_0_full_uncertainty_aep.csv
touch analysis/a53e98e4-0197-4513-be6d-49836e406aaa/output/il_0_full_uncertainty_oep.csv

# Archive the outputs ready for download
tar cvzf download/25892e17-80f6-415f-9c65-7395632f0223.tar.gz analysis/a53e98e4-0197-4513-be6d-49836e406aaa/output

# Tidy up
# rm -rf analysis/a53e98e4-0197-4513-be6d-49836e406aaa
