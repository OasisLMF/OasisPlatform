#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib
import io
import inspect
import json
import os
import shutil
import sys
import tarfile
import time
import unittest

TEST_DIRECTORY = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
TEST_DATA_DIRECTORY = os.path.abspath(os.path.join(TEST_DIRECTORY, 'data'))
LIB_PATH = os.path.abspath(os.path.join(TEST_DIRECTORY, '..', 'src'))
sys.path.append(LIB_PATH)

import oasis_utils.kparse as kparse

KPARSE_INPUT_FOLDER = os.path.join(TEST_DIRECTORY, "kparse_input")
KPARSE_OUTPUT_FOLDER = os.path.join(TEST_DIRECTORY, "kparse_output")
KPARSE_REFERENCE_FOLDER = os.path.join(TEST_DIRECTORY, "kparse_reference")


class Test_KparseTests(unittest.TestCase):
    '''
    KParse tests - converting analysis settings to Ktools execution bash script
    '''

    @classmethod
    def setUpClass(cls):
        if os.path.exists(KPARSE_OUTPUT_FOLDER):
            shutil.rmtree(KPARSE_OUTPUT_FOLDER)
        os.makedirs(KPARSE_OUTPUT_FOLDER)

    def md5(self, fname):
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def run_kparse(self, name, num_partitions):

        input_filename = os.path.join(
            KPARSE_INPUT_FOLDER, 
            "{}.json".format(name))
        output_filename = os.path.join(
            KPARSE_OUTPUT_FOLDER,
            "{}_{}_partition.sh".format(name, num_partitions))

        with open(input_filename) as file:
            analysis_settings = json.load(file)['analysis_settings']

        kparse.genbash(
            num_partitions,
            analysis_settings,
            output_filename)

    def check(self, name):
        output_filename = os.path.join(
            KPARSE_OUTPUT_FOLDER, 
            "{}.sh".format(name))
        reference_filename = os.path.join(
            KPARSE_REFERENCE_FOLDER, 
            "{}.sh".format(name))
        output_md5 = self.md5(output_filename)
        reference_md5 = self.md5(reference_filename)

        return (output_md5 == reference_md5)

    # def test_no_outputs(self):
    #     assert(True)

    def test_gul_summarycalc_1_partition(self):
        self.run_kparse("gul_summarycalc_1_output", 1)
        assert(self.check("gul_summarycalc_1_output_1_partition"))

    def test_gul_summarycalc_20_partition(self):
        self.run_kparse("gul_summarycalc_1_output", 20)
        assert(self.check("gul_summarycalc_1_output_20_partition"))

    def test_gul_eltcalc_1_partition(self):
        self.run_kparse("gul_eltcalc_1_output", 1)
        assert(self.check("gul_eltcalc_1_output_1_partition"))

    def test_gul_eltcalc_20_partition(self):
        self.run_kparse("gul_eltcalc_1_output", 20)
        assert(self.check("gul_eltcalc_1_output_20_partition"))

    def test_gul_aalcalc_1_partition(self):
        self.run_kparse("gul_aalcalc_1_output", 1)
        assert(self.check("gul_aalcalc_1_output_1_partition"))

    def test_gul_aalcalc_20_partition(self):
        self.run_kparse("gul_aalcalc_1_output", 20)
        assert(self.check("gul_aalcalc_1_output_20_partition"))

    def test_gul_pltcalc_1_partition(self):
        self.run_kparse("gul_pltcalc_1_output", 1)
        assert(self.check("gul_pltcalc_1_output_1_partition"))

    def test_gul_pltcalc_20_partition(self):
        self.run_kparse("gul_pltcalc_1_output", 20)
        assert(self.check("gul_pltcalc_1_output_20_partition"))

    def test_gul_agg_fu_lec_1_partition(self):
        self.run_kparse("gul_agg_fu_lec_1_output", 1)
        assert(self.check("gul_agg_fu_lec_1_output_1_partition"))

    def test_gul_agg_fu_lec_20_partition(self):
        self.run_kparse("gul_agg_fu_lec_1_output", 20)
        assert(self.check("gul_agg_fu_lec_1_output_20_partition"))

    def test_gul_agg_fu_lec_1_partition(self):
        self.run_kparse("gul_occ_fu_lec_1_output", 1)
        assert(self.check("gul_occ_fu_lec_1_output_1_partition"))

    def test_gul_agg_fu_lec_20_partition(self):
        self.run_kparse("gul_occ_fu_lec_1_output", 20)
        assert(self.check("gul_occ_fu_lec_1_output_20_partition"))

    def test_gul_agg_ws_lec_1_partition(self):
        self.run_kparse("gul_agg_ws_lec_1_output", 1)
        assert(self.check("gul_agg_ws_lec_1_output_1_partition"))

    def test_gul_agg_ws_lec_20_partition(self):
        self.run_kparse("gul_agg_ws_lec_1_output", 20)
        assert(self.check("gul_agg_ws_lec_1_output_20_partition"))

    def test_gul_occ_ws_lec_1_partition(self):
        self.run_kparse("gul_occ_ws_lec_1_output", 1)
        assert(self.check("gul_occ_ws_lec_1_output_1_partition"))

    def test_gul_occ_ws_lec_20_partition(self):
        self.run_kparse("gul_occ_ws_lec_1_output", 20)
        assert(self.check("gul_occ_ws_lec_1_output_20_partition"))

    def test_gul_agg_ws_mean_lec_1_partition(self):
        self.run_kparse("gul_agg_ws_mean_lec_1_output", 1)
        assert(self.check("gul_agg_ws_mean_lec_1_output_1_partition"))

    def test_gul_agg_ws_mean_lec_20_partition(self):
        self.run_kparse("gul_agg_ws_mean_lec_1_output", 20)
        assert(self.check("gul_agg_ws_mean_lec_1_output_20_partition"))

    def test_gul_occ_ws_mean_lec_1_partition(self):
        self.run_kparse("gul_occ_ws_mean_lec_1_output", 1)
        assert(self.check("gul_occ_ws_mean_lec_1_output_1_partition"))

    def test_gul_occ_ws_mean_lec_20_partition(self):
        self.run_kparse("gul_occ_ws_mean_lec_1_output", 20)
        assert(self.check("gul_occ_ws_mean_lec_1_output_20_partition"))

    def test_il_agg_sample_mean_lec_1_partition(self):
        self.run_kparse("il_agg_sample_mean_lec_1_output", 1)
        assert(self.check("il_agg_sample_mean_lec_1_output_1_partition"))

    def test_il_agg_sample_mean_lec_20_partition(self):
        self.run_kparse("il_agg_sample_mean_lec_1_output", 20)
        assert(self.check("il_agg_sample_mean_lec_1_output_20_partition"))

    def test_il_occ_sample_mean_lec_1_partition(self):
        self.run_kparse("il_occ_sample_mean_lec_1_output", 1)
        assert(self.check("il_occ_sample_mean_lec_1_output_1_partition"))

    def test_il_occ_sample_mean_lec_20_partition(self):
        self.run_kparse("il_occ_sample_mean_lec_1_output", 20)
        assert(self.check("il_occ_sample_mean_lec_1_output_20_partition"))

    def test_il_summarycalc_1_partition(self):
        self.run_kparse("il_summarycalc_1_output", 1)
        assert(self.check("il_summarycalc_1_output_1_partition"))

    def test_il_summarycalc_20_partition(self):
        self.run_kparse("il_summarycalc_1_output", 20)
        assert(self.check("il_summarycalc_1_output_20_partition"))

    def test_il_eltcalc_1_partition(self):
        self.run_kparse("il_eltcalc_1_output", 1)
        assert(self.check("il_eltcalc_1_output_1_partition"))

    def test_il_eltcalc_20_partition(self):
        self.run_kparse("il_eltcalc_1_output", 20)
        assert(self.check("il_eltcalc_1_output_20_partition"))

    def test_il_aalcalc_1_partition(self):
        self.run_kparse("il_aalcalc_1_output", 1)
        assert(self.check("il_aalcalc_1_output_1_partition"))

    def test_il_aalcalc_20_partition(self):
        self.run_kparse("il_aalcalc_1_output", 20)
        assert(self.check("il_aalcalc_1_output_20_partition"))

    def test_il_pltcalc_1_partition(self):
        self.run_kparse("il_pltcalc_1_output", 1)
        assert(self.check("il_pltcalc_1_output_1_partition"))

    def test_il_pltcalc_20_partition(self):
        self.run_kparse("il_pltcalc_1_output", 20)
        assert(self.check("il_pltcalc_1_output_20_partition"))

    def test_il_agg_fu_lec_1_partition(self):
        self.run_kparse("il_agg_fu_lec_1_output", 1)
        assert(self.check("il_agg_fu_lec_1_output_1_partition"))

    def test_il_agg_fu_lec_20_partition(self):
        self.run_kparse("il_agg_fu_lec_1_output", 20)
        assert(self.check("il_agg_fu_lec_1_output_20_partition"))

    def test_il_agg_fu_lec_1_partition(self):
        self.run_kparse("il_occ_fu_lec_1_output", 1)
        assert(self.check("il_occ_fu_lec_1_output_1_partition"))

    def test_il_agg_fu_lec_20_partition(self):
        self.run_kparse("il_occ_fu_lec_1_output", 20)
        assert(self.check("il_occ_fu_lec_1_output_20_partition"))

    def test_il_agg_ws_lec_1_partition(self):
        self.run_kparse("il_agg_ws_lec_1_output", 1)
        assert(self.check("il_agg_ws_lec_1_output_1_partition"))

    def test_il_agg_ws_lec_20_partition(self):
        self.run_kparse("il_agg_ws_lec_1_output", 20)
        assert(self.check("il_agg_ws_lec_1_output_20_partition"))

    def test_il_occ_ws_lec_1_partition(self):
        self.run_kparse("il_occ_ws_lec_1_output", 1)
        assert(self.check("il_occ_ws_lec_1_output_1_partition"))

    def test_il_occ_ws_lec_20_partition(self):
        self.run_kparse("il_occ_ws_lec_1_output", 20)
        assert(self.check("il_occ_ws_lec_1_output_20_partition"))

    def test_il_agg_ws_mean_lec_1_partition(self):
        self.run_kparse("il_agg_ws_mean_lec_1_output", 1)
        assert(self.check("il_agg_ws_mean_lec_1_output_1_partition"))

    def test_il_agg_ws_mean_lec_20_partition(self):
        self.run_kparse("il_agg_ws_mean_lec_1_output", 20)
        assert(self.check("il_agg_ws_mean_lec_1_output_20_partition"))

    def test_il_occ_ws_mean_lec_1_partition(self):
        self.run_kparse("il_occ_ws_mean_lec_1_output", 1)
        assert(self.check("il_occ_ws_mean_lec_1_output_1_partition"))

    def test_il_occ_ws_mean_lec_20_partition(self):
        self.run_kparse("il_occ_ws_mean_lec_1_output", 20)
        assert(self.check("il_occ_ws_mean_lec_1_output_20_partition"))

    def test_il_agg_sample_mean_lec_1_partition(self):
        self.run_kparse("il_agg_sample_mean_lec_1_output", 1)
        assert(self.check("il_agg_sample_mean_lec_1_output_1_partition"))

    def test_il_agg_sample_mean_lec_20_partition(self):
        self.run_kparse("il_agg_sample_mean_lec_1_output", 20)
        assert(self.check("il_agg_sample_mean_lec_1_output_20_partition"))

    def test_il_occ_sample_mean_lec_1_partition(self):
        self.run_kparse("il_occ_sample_mean_lec_1_output", 1)
        assert(self.check("il_occ_sample_mean_lec_1_output_1_partition"))

    def test_il_occ_sample_mean_lec_20_partition(self):
        self.run_kparse("il_occ_sample_mean_lec_1_output", 20)
        assert(self.check("il_occ_sample_mean_lec_1_output_20_partition"))

    def test_il_occ_sample_mean_lec_20_partition(self):
        self.run_kparse("il_occ_sample_mean_lec_1_output", 20)
        assert(self.check("il_occ_sample_mean_lec_1_output_20_partition"))

    def test_all_calcs_1_partition(self):
        self.run_kparse("all_calcs_1_output", 1)
        assert(self.check("all_calcs_1_output_1_partition"))

    def test_all_calcs_20_partition(self):
        self.run_kparse("all_calcs_1_output", 20)
        assert(self.check("all_calcs_1_output_20_partition"))

    def test_all_calcs_40_partition(self):
        self.run_kparse("all_calcs_1_output", 40)
        assert(self.check("all_calcs_1_output_40_partition"))

    def test_gul_no_lec_1_output_1_partition(self):
        self.run_kparse("gul_no_lec_1_output", 1)
        assert(self.check("gul_no_lec_1_output_1_partition"))

    def test_gul_no_lec_1_output_2_partition(self):
        self.run_kparse("gul_no_lec_1_output", 2)
        assert(self.check("gul_no_lec_1_output_2_partition"))

    def test_gul_no_lec_2_output_1_partition(self):
        self.run_kparse("gul_no_lec_2_output", 1)
        assert(self.check("gul_no_lec_2_output_1_partition"))

    def test_gul_no_lec_2_output_2_partitions(self):
        self.run_kparse("gul_no_lec_2_output", 2)
        assert(self.check("gul_no_lec_2_output_2_partition"))

    def test_gul_lec_1_output_1_partition(self):
        self.run_kparse("gul_lec_1_output", 1)
        assert(self.check("gul_lec_1_output_1_partition"))

    def test_gul_lec_1_output_2_partitions(self):
        self.run_kparse("gul_lec_1_output", 2)
        assert(self.check("gul_lec_1_output_2_partition"))

    def test_gul_lec_2_output_1_partition(self):
        self.run_kparse("gul_lec_2_output", 1)
        assert(self.check("gul_lec_2_output_1_partition"))

    def test_gul_lec_2_output_2_partitions(self):
        self.run_kparse("gul_lec_2_output", 2)
        assert(self.check("gul_lec_2_output_2_partition"))

    def test_il_no_lec_1_output_1_partition(self):
        self.run_kparse("il_no_lec_1_output", 1)
        assert(self.check("il_no_lec_1_output_1_partition"))

    def test_il_no_lec_1_output_2_partition(self):
        self.run_kparse("il_no_lec_1_output", 2)
        assert(self.check("il_no_lec_1_output_2_partition"))

    def test_il_no_lec_2_output_1_partition(self):
        self.run_kparse("il_no_lec_2_output", 1)
        assert(self.check("il_no_lec_2_output_1_partition"))

    def test_il_no_lec_2_output_2_partitions(self):
        self.run_kparse("il_no_lec_2_output", 2)
        assert(self.check("il_no_lec_2_output_2_partition"))

    def test_il_lec_1_output_1_partition(self):
        self.run_kparse("il_lec_1_output", 1)
        assert(self.check("il_lec_1_output_1_partition"))

    def test_il_lec_1_output_2_partitions(self):
        self.run_kparse("il_lec_1_output", 2)
        assert(self.check("il_lec_1_output_2_partition"))

    def test_il_lec_2_output_1_partition(self):
        self.run_kparse("il_lec_2_output", 1)
        assert(self.check("il_lec_2_output_1_partition"))

    def test_il_lec_2_output_2_partitions(self):
        self.run_kparse("il_lec_2_output", 2)
        assert(self.check("il_lec_2_output_2_partition"))

    def test_gul_il_no_lec_1_output_1_partition(self):
        self.run_kparse("gul_il_no_lec_1_output", 1)
        assert(self.check("gul_il_no_lec_1_output_1_partition"))

    def test_gul_il_no_lec_1_output_2_partition(self):
        self.run_kparse("gul_il_no_lec_1_output", 2)
        assert(self.check("gul_il_no_lec_1_output_2_partition"))

    def test_gul_il_no_lec_2_output_1_partition(self):
        self.run_kparse("gul_il_no_lec_2_output", 1)
        assert(self.check("gul_il_no_lec_2_output_1_partition"))

    def test_gul_il_no_lec_2_output_2_partitions(self):
        self.run_kparse("gul_il_no_lec_2_output", 2)
        assert(self.check("gul_il_no_lec_2_output_2_partition"))

    def test_gul_il_lec_1_output_1_partition(self):
        self.run_kparse("gul_il_lec_1_output", 1)
        assert(self.check("gul_il_lec_1_output_1_partition"))

    def test_gul_il_lec_1_output_2_partitions(self):
        self.run_kparse("gul_il_lec_1_output", 2)
        assert(self.check("gul_il_lec_1_output_2_partition"))

    def test_gul_il_lec_2_output_1_partition(self):
        self.run_kparse("gul_il_lec_2_output", 1)
        assert(self.check("gul_il_lec_2_output_1_partition"))

    def test_gul_il_lec_2_output_2_partitions(self):
        self.run_kparse("gul_il_lec_2_output", 2)
        assert(self.check("gul_il_lec_2_output_2_partition"))

    def test_gul_il_lec_2_output_10_partitions(self):
        self.run_kparse("gul_il_lec_2_output", 10)
        assert(self.check("gul_il_lec_2_output_10_partition"))

    def test_analysis_settings_1(self):
        self.run_kparse("analysis_settings_1", 1)
        assert(self.check("analysis_settings_1_1_partition"))

    def test_analysis_settings_2(self):
        self.run_kparse("analysis_settings_2", 1)
        assert(self.check("analysis_settings_2_1_partition"))

if __name__ == '__main__':
    unittest.main()

