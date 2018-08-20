#! /usr/bin/python

import os
import pandas as pd

from argparse import Namespace
from oasislmf.exposures.reinsurance_layer import \
    validate_reinsurance_structures, load_oed_dfs, generate_files_for_reinsurance

oed_dir = "tests/reinsurance/oed"
direct_oasis_files_dir = "tests/reinsurance/input/csv"
areaperil_id = 600001
vulnerability_id = 10

(account_df, location_df, ri_info_df, ri_scope_df, do_reinsurance) = load_oed_dfs(oed_dir)

# Direct layers are done by Flamingo - just load the examples
items = pd.read_csv(
            os.path.join(direct_oasis_files_dir, "items.csv"))
coverages = pd.read_csv(
            os.path.join(direct_oasis_files_dir, "coverages.csv"))
fm_xrefs = pd.read_csv(
            os.path.join(direct_oasis_files_dir, "fm_xref.csv"))
xref_descriptions = pd.read_csv(
            os.path.join(direct_oasis_files_dir, "xref_descriptions.csv"))

(is_valid, reisurance_layers) = validate_reinsurance_structures(
    account_df, location_df, ri_info_df, ri_scope_df)

if not is_valid:
    print("Reinsuarnce structure not valid")
    for reinsurance_layer in reisurance_layers:
        if not reinsurance_layer.is_valid:
            print("Inuring layer {} invalid:".format(
                reinsurance_layer.inuring_priority))
            for validation_message in reinsurance_layer.validation_messages:
                print("\t{}".format(validation_message))
            exit(0)

generate_files_for_reinsurance(
        account_df,
        location_df,
        items,
        coverages,
        fm_xrefs,
        xref_descriptions,
        ri_info_df,
        ri_scope_df,
        direct_oasis_files_dir)

# Run the analysis on a local test system

import oasislmf.cmd.test

args = Namespace(
    api_server_url='http://localhost:8001',
    analysis_settings_file='tests/reinsurance/analysis_settings.json',
    input_directory='tests/reinsurance/input/csv',
    output_directory='tests/reinsurance/output',
    num_analyses=1,
    health_check_attempts=1
)

cmd = oasislmf.cmd.test.TestModelApiCmd()
cmd.action(args)