#!/usr/bin/python

import argparse
import csv
import os
import random
import struct
import time
import subprocess
from numpy import random as np_random

parser = argparse.ArgumentParser(description='Create a set of test model \
                                 data.')
parser.add_argument('-num_area_perils', type=int, default=100,
                    help="The total number of area perils")
parser.add_argument('-num_vulnerabilities', type=int, default=10,
                    help="The total number of vulnerabilies.")
parser.add_argument('-num_events', type=int, default=1000,
                    help="The total number of events.")
parser.add_argument('-num_area_perils_per_event', type=int, default=10,
                    help="The number of area perils impacted per event.")
parser.add_argument('-num_intensity_bins', type=int, default=100,
                    help="The total number of intensity bins.")
parser.add_argument('-no_intensity_uncertainty', action="store_true",
                    help="No intensity uncertainty.")
parser.add_argument('-intensity_sparseness', type=float, default=0.5,
                    help="The percentage of bins impacted for an event \
                    and area peril.")
parser.add_argument('-num_damage_bins', type=int, default=102,
                    help="The total number of intensity bins.")
parser.add_argument('-vulnerability_sparseness', type=float, default=0.5,
                    help="The percentage of bins impacted for a vulnerability \
                    at an intensity level.")
parser.add_argument('-do_csv', action="store_true",
                    help="Output CSV files.")
parser.add_argument('-data_dir', type=str, default="./",
                    help="Output directory for data files.")
parser.add_argument('-repeatable', action="store_true",
                    help="Create repeatable data.")
parser.add_argument('-num_period', type=int, default=1000,
                    help="The total number of period")
parser.add_argument('-num_sample', type=int, default=100000,
                    help="The total number of sample")
parser.add_argument('-num_location', type=int, default=100,
                    help="The total number of locations")
parser.add_argument('-num_coverage_per_location', type=int, default=3,
                    help="The number of coverages per location")
parser.add_argument('-check_case', action="store_true",
                    help="check if a policy_id for each coverage.")
parser.add_argument('-level_check', action="store_true",
                    help="check if there is a level 3.")
parser.add_argument('-allocrule', action="store_true",
                    help="check if there is a allocrule.")

args = parser.parse_args()

# Is there a better way to import the args namespace?
num_area_perils = args.num_area_perils
num_vulnerabilities = args.num_vulnerabilities
num_events = args.num_events
num_area_perils_per_event = args.num_area_perils_per_event
num_intensity_bins = args.num_intensity_bins
no_intensity_uncertainty = False  # args.no_intensity_uncertainty
intensity_sparseness = args.intensity_sparseness
num_damage_bins = args.num_damage_bins
vulnerability_sparseness = args.vulnerability_sparseness
data_dir = 'data'  # args.data_dir
do_csv = True  # True for creating csv file
repeatable = False  # args.repeatable
num_period = args.num_period
num_sample = args.num_sample
num_location = args.num_location
num_coverage_per_location = args.num_coverage_per_location
# True if each coverage has a policy_id
# False if all coverage have a same policy_id
check_case = False
# True if there is a level 3
level_check = True
# True if there is a allocrule_id for fm_profile.csv
allocrule = False


def generate_test_data(
        allocrule,
        check_case,
        level_check,
        num_period,
        num_location,
        num_coverage_per_location,
        num_area_perils,
        num_vulnerabilities,
        num_events,
        num_area_perils_per_event,
        num_intensity_bins,
        no_intensity_uncertainty,
        intensity_sparseness,
        num_damage_bins,
        vulnerability_sparseness,
        data_dir,
        do_csv,
        repeatable,
        log=False):

    # Data files
    CSV_FILE_SUFFIX = ".csv"
    INDEX_FILE_SUFFIX = ".idx"

    # Check the data files
    if not os.path.isdir(data_dir):
        if log:
            print "Data directory does not exist: {}".format(data_dir)
        quit()

    data_dir = data_dir + "/"
    item_filename_csv = data_dir + "items" + CSV_FILE_SUFFIX
    vulnerability_filename_csv = data_dir + "vulnerability" + CSV_FILE_SUFFIX
    event_filename_csv = data_dir + "footprint" + CSV_FILE_SUFFIX
    event_index_filename_bin = data_dir + "footprint" + INDEX_FILE_SUFFIX
    damage_bin_dict_csv = data_dir + "damage_bin_dict" + CSV_FILE_SUFFIX
    fm_policytc_filename_csv = data_dir + "fm_policytc" + CSV_FILE_SUFFIX
    fm_profile_filename_csv = data_dir + "fm_profile" + CSV_FILE_SUFFIX
    fm_programme_filename_csv = data_dir + "fm_programme" + CSV_FILE_SUFFIX
    xref_filename_csv = data_dir + "fm_xref" + CSV_FILE_SUFFIX
    fm_sumxref_filename_csv = data_dir + "fmsummaryxref" + CSV_FILE_SUFFIX
    gulsumxref_filename_csv = data_dir + "gulsummaryxref" + CSV_FILE_SUFFIX
    coverage_filename_csv = data_dir + "coverages" + CSV_FILE_SUFFIX
    events_filename_csv = data_dir + "events" + CSV_FILE_SUFFIX
    occurrence_filename_csv = data_dir + "occurrence" + CSV_FILE_SUFFIX
    random_filename_csv = data_dir + "random" + CSV_FILE_SUFFIX

    # If we want repeatable data use a fixed seed
    if repeatable:
        random.seed(999)
        np_random.seed(999)
    else:
        random.seed()
        np_random.seed()

    # Generate occurrence_id
    try:
        if log:
            print"Generating occurrence data"
        t0 = time.clock()
        if do_csv:
            occurrence_file_csv = open(occurrence_filename_csv, "wb")
            occurrence_csv_writer = csv.writer(occurrence_file_csv)
            occurrence_csv_writer.writerow([
                "event_id", "period_no", "occ_year", "occ_month", "occ_day"]
            )
        count = 1
        for count in range(1, num_events + 1):
            event_id = count
            count = count + 1
            period_no = random.randint(1, num_period)
            occ_year = period_no
            occ_month = random.randint(1, 13)
            occ_day = random.randint(1, 28)
            if do_csv:
                occurrence_csv_writer.writerow(
                    [event_id, period_no, occ_year, occ_month, occ_day]
                )
        if do_csv:
            occurrence_file_csv.close()
        t1 = time.clock()
        if log:
            print "Generated occurrence data in {0:.2f}s".format(t1 - t0)
    except Exception, e:
        print Exception, ":", e
        exit()

    # Generate a list of random number
    try:
        if log:
            print "Generating random number"
        t1 = time.clock()
        if do_csv:
            random_file_csv = open(random_filename_csv, "wb")
            random_csv_writer = csv.writer(random_file_csv)
        for count in range(1, num_sample + 1):
            if count == 1:
                rand = 0
            else:
                rand = random.uniform(0, 1)
            if do_csv:
                random_csv_writer.writerow(
                    [rand]
                )
        if do_csv:
            random_file_csv.close()
        t1 = time.clock()
        if log:
            print "Generated random number in {0:.2f}s".format(t1 - t0)
    except Exception, e:
        print Exception, ":", e
        exit()

    # Generate the Coverage data
    try:
        if log:
            print "Generating coverage data"
        t0 = time.clock()
        if do_csv:
            coverage_file_csv = open(coverage_filename_csv, "wb")
            coverage_csv_writer = csv.writer(coverage_file_csv)
            coverage_csv_writer.writerow(["coverage_id", "tiv"])
        for coverage_id in range(1,
                                 num_location * num_coverage_per_location + 1):
            # generate a uniform distributed number for total insured value
            tiv = random.uniform(1, 100000)
            if do_csv:
                coverage_csv_writer.writerow([coverage_id, tiv])
        if do_csv:
            coverage_file_csv.close()
        t1 = time.clock()
        if log:
            print "Generated coverage data in {0:.2f}s".format(t1 - t0)
    except Exception, e:
        print Exception, ":", e
        exit()

    # Generate summary data
    try:
        if log:
            print "Generating summary data"
        t0 = time.clock()
        if do_csv:
            gulsumxref_file_csv = open(gulsumxref_filename_csv, "wb")
            gulsumxref_csv_writer = csv.writer(gulsumxref_file_csv)
            gulsumxref_csv_writer.writerow([
                "coverage_id", "summary_id", "summaryset_id"])
            sumxref_file_csv = open(fm_sumxref_filename_csv, "wb")
            sumxref_csv_writer = csv.writer(sumxref_file_csv)
            sumxref_csv_writer.writerow([
                "output_id", "summary_id", "summaryset_id"])
        summary_id = 1
        summaryset_id = 1
        output_id = 1
        for coverage_id in range(1,
                                 num_location * num_coverage_per_location + 1):
            if do_csv:
                gulsumxref_csv_writer.writerow([
                    coverage_id, summary_id, summaryset_id])
        if allocrule:
            for coverage_id in range(1,
                                     num_location *
                                     num_coverage_per_location +
                                     1):
                sumxref_csv_writer.writerow([
                    output_id, summary_id, summaryset_id])
                output_id = output_id + 1
        else:
            sumxref_csv_writer.writerow([output_id, summary_id, summaryset_id])
        if do_csv:
            gulsumxref_file_csv.close()
            sumxref_file_csv.close()
        t1 = time.clock()
        if log:
            print "Generated summary data in {0:.2f}s".format(t1 - t0)
    except Exception, e:
        print Exception, ":", e
        exit()

    # Generate the item and fm data
    try:
        if log:
            print "Generating exposure data"
        t0 = time.clock()
        if do_csv:
            item_file_csv = open(item_filename_csv, "wb")
            item_csv_writer = csv.writer(item_file_csv)
            item_csv_writer.writerow(
                ["item_id", "coverage_id", "area_peril_id",
                 "vulnerability_id", "group_id"])
        policytc_file_csv = open(fm_policytc_filename_csv, "wb")
        policytc_csv_writer = csv.writer(policytc_file_csv)
        policytc_csv_writer.writerow(["layer_id", "level_id",
                                      "agg_id", "PolicyTC_id"])
        profile_file_csv = open(fm_profile_filename_csv, "wb")
        profile_csv_writer = csv.writer(profile_file_csv)
        profile_csv_writer.writerow(
            ["policytc_id", "calcrule_id", "allocrule_id",
             "ccy_id", "deductible", "limits",
             "share_prop_of_lim", "deductible_prop_of_loss",
             "limit_prop_of_loss", "deductible_prop_of_tiv",
             "limit_prop_of_tiv", "deductible_prop_of_limit"])
        programme_file_csv = open(fm_programme_filename_csv, "wb")
        programme_csv_writer = csv.writer(programme_file_csv)
        programme_csv_writer.writerow(["from_agg_id", "level_id", "to_agg_id"])
        xref_file_csv = open(xref_filename_csv, "wb")
        xref_csv_writer = csv.writer(xref_file_csv)
        xref_csv_writer.writerow(["output_id", "agg_id", "layer_id"])
        # check if there is a level 3
        if level_check:
            num_level = 3
        else:
            num_level = 2
        item_id = 1
        output_id = 1
        for level_id in range(1, num_level + 1):
            # Level 1 (coverage level)
            if level_id == 1:
                calcrule_id = 12
                allocrule_id = 0
                ccy_id = 2
                deductible = 100
                limits = 0
                share_prop_of_lim = 0
                deductible_prop_of_loss = 0
                limit_prop_of_loss = 0
                deductible_prop_of_tiv = 0
                limit_prop_of_tiv = 0
                deductible_prop_of_limit = 0
                layer_id = 1
                if check_case:  # if each coverage has a different policy_id
                    for policy_id in range(1,
                                           num_location *
                                           num_coverage_per_location +
                                           1):
                        policytc_id = policy_id
                        agg_id = policy_id
                        policytc_csv_writer.writerow(
                            [layer_id, level_id, agg_id, policytc_id])
                        profile_csv_writer.writerow(
                            [policytc_id, calcrule_id, allocrule_id,
                             ccy_id, deductible, limits,
                             share_prop_of_lim, deductible_prop_of_loss,
                             limit_prop_of_loss, deductible_prop_of_tiv,
                             limit_prop_of_tiv, deductible_prop_of_limit])
                        from_agg_id = policy_id
                        to_agg_id = policy_id
                        programme_csv_writer.writerow([
                            from_agg_id, level_id, to_agg_id])
                else:  # if one policy_id applies to all coverages
                    policytc_id = 1
                    profile_csv_writer.writerow(
                        [policytc_id, calcrule_id, allocrule_id,
                         ccy_id, deductible, limits,
                         share_prop_of_lim, deductible_prop_of_loss,
                         limit_prop_of_loss, deductible_prop_of_tiv,
                         limit_prop_of_tiv, deductible_prop_of_limit])
                    for policy_id in range(1,
                                           num_location *
                                           num_coverage_per_location +
                                           1):
                        agg_id = policy_id
                        policytc_csv_writer.writerow(
                            [layer_id, level_id, agg_id, policytc_id])
                        from_agg_id = policy_id
                        to_agg_id = policy_id
                        programme_csv_writer.writerow(
                            [from_agg_id, level_id, to_agg_id])

            # Level 2 (location level)
            if level_id == 2:
                layer_id = 1
                from_agg_id = 1
                to_agg_id = 1
                agg_id = 1
                calcrule_id = 1
                allocrule_id = 0
                ccy_id = 2
                deductible = 0
                limits = 80000
                share_prop_of_lim = 0
                deductible_prop_of_loss = 0
                limit_prop_of_loss = 0
                deductible_prop_of_tiv = 0
                limit_prop_of_tiv = 0
                deductible_prop_of_limit = 0
                if check_case:  # if each location has a different policy_id
                    start_pos = num_location * \
                        num_coverage_per_location + 1
                    end_pos = num_location * \
                        (num_coverage_per_location + level_id - 1) + 1
                    for policy_id in range(start_pos, end_pos):
                        policytc_id = policy_id
                        policytc_csv_writer.writerow(
                            [layer_id, level_id, agg_id, policytc_id])
                        profile_csv_writer.writerow(
                            [policytc_id, calcrule_id, allocrule_id,
                             ccy_id, deductible, limits,
                             share_prop_of_lim, deductible_prop_of_loss,
                             limit_prop_of_loss, deductible_prop_of_tiv,
                             limit_prop_of_tiv, deductible_prop_of_limit])
                        agg_id = agg_id + 1
                        for policy_item_id in range(1,
                                                    num_coverage_per_location +
                                                    1):
                            programme_csv_writer.writerow(
                                [from_agg_id, level_id, to_agg_id])
                            from_agg_id = from_agg_id + 1
                        to_agg_id = to_agg_id + 1
                else:  # if one policy_id applies to all locations
                    policytc_id = 2
                    profile_csv_writer.writerow(
                        [policytc_id, calcrule_id, allocrule_id,
                         ccy_id, deductible, limits,
                         share_prop_of_lim, deductible_prop_of_loss,
                         limit_prop_of_loss, deductible_prop_of_tiv,
                         limit_prop_of_tiv, deductible_prop_of_limit])
                    for policy_id in range(1, num_location + 1):
                        policytc_csv_writer.writerow(
                            [layer_id, level_id, agg_id, policytc_id])
                        agg_id = agg_id + 1
                        for policy_item_id in range(1,
                                                    num_coverage_per_location +
                                                    1):
                            programme_csv_writer.writerow(
                                [from_agg_id, level_id, to_agg_id])
                            from_agg_id = from_agg_id + 1
                        to_agg_id = to_agg_id + 1
                if level_check:
                    continue
                else:
                    for agg_id in range(1, num_location + 1):
                        xref_csv_writer.writerow([output_id, agg_id, layer_id])
                        output_id = output_id + 1

            # Level 3 (whole portfolio)
            if level_id == 3:
                if check_case:
                    policytc_id = num_location * \
                        (num_coverage_per_location + 1) + 1
                else:
                    policytc_id = 3
                layer_id = 1
                agg_id = 1
                policytc_csv_writer.writerow(
                    [layer_id, level_id, agg_id, policytc_id])
                calcrule_id = 2
                if allocrule:  # if there is a allocrule
                    allocrule_id = 1
                else:  # if there is no allocrule
                    allocrule_id = 0
                ccy_id = 2
                deductible = 0
                limits = 1000000
                share_prop_of_lim = 0.1
                deductible_prop_of_loss = 0
                limit_prop_of_loss = 0
                deductible_prop_of_tiv = 0
                limit_prop_of_tiv = 0
                deductible_prop_of_limit = 0
                profile_csv_writer.writerow(
                    [policytc_id, calcrule_id, allocrule_id,
                     ccy_id, deductible, limits,
                     share_prop_of_lim, deductible_prop_of_loss,
                     limit_prop_of_loss, deductible_prop_of_tiv,
                     limit_prop_of_tiv, deductible_prop_of_limit])
                for from_agg_id in range(1, num_location + 1):
                    to_agg_id = 1
                    programme_csv_writer.writerow(
                        [from_agg_id, level_id, to_agg_id])
                output_id = 1
                if allocrule:
                    for agg_id in range(1,
                                        num_location *
                                        num_coverage_per_location + 1):
                        xref_csv_writer.writerow([output_id, agg_id, layer_id])
                        output_id = output_id + 1
                else:
                    xref_csv_writer.writerow([output_id, agg_id, layer_id])

        group_id = 0
        count = 0
        times = 0
        for item_id in range(1,
                             num_location *
                             num_coverage_per_location + 1):
            coverage_id = item_id
            if item_id == 1:
                area_peril_id = random.randint(1, num_area_perils)
                times = random.randint(1, 10)
            else:
                if count == times:
                    times = random.randint(1, 10)
                    area_peril_id = random.randint(1, num_area_perils)
                    count = 0
            count = count + 1
            vulnerability_id = random.randint(1, num_vulnerabilities)
            group_id = group_id + 1
            if do_csv:
                item_csv_writer.writerow(
                    [item_id, coverage_id, area_peril_id,
                     vulnerability_id, group_id])
        if do_csv:
            item_file_csv.close()
        policytc_file_csv.close()
        profile_file_csv.close()
        programme_file_csv.close()
        xref_file_csv.close()
        t1 = time.clock()
        if log:
            print "Generated item and fm data in {0:.2f}s".format(t1 - t0)
    except Exception, e:
        print Exception, ":", e
        exit()

    # Generate the vulnerability data
    try:
        if log:
            print "Generating vulnerability data"
        t0 = time.clock()
        if do_csv:
            vulnerability_file_csv = file(vulnerability_filename_csv, "wb")
            vulnerability_csv_writer = csv.writer(vulnerability_file_csv)
            vulnerability_csv_writer.writerow(["vulnerability_id",
                                               "intensity_bin_index",
                                               "damage_bin_index", "prob"])
        for vulnerability_id in range(1, num_vulnerabilities + 1):
            vulnerability = list()
            for intensity_bin_index in range(1, num_intensity_bins + 1):
                vulnerability.append(list())
                total = 0.0
                for damage_bin_index in range(1, num_damage_bins + 1):
                    sample = 0
                    if random.uniform(0, 1) < vulnerability_sparseness:
                        sample = random.uniform(0, 1)
                    total = total + sample
                    vulnerability[intensity_bin_index - 1].append(sample)
                for damage_bin_index in range(1,
                                              num_damage_bins + 1):
                    if vulnerability[
                            intensity_bin_index-1][damage_bin_index-1] == 0:
                        probability = 0
                    else:
                        probability = vulnerability[
                            intensity_bin_index - 1][damage_bin_index - 1] / \
                            total
                    if do_csv:
                        vulnerability_csv_writer.writerow([
                            vulnerability_id,
                            intensity_bin_index,
                            damage_bin_index,
                            probability])
        if do_csv:
            vulnerability_file_csv.close()
        t1 = time.clock()
        if log:
            print "Generated vulnerability data in {0:.2f}s".format(t1 - t0)
    except Exception, e:
        print Exception, ":", e
        exit()

    # Generate the event data
    try:
        if log:
            print "Generating event data"
        t0 = time.clock()
        if do_csv:
            event_file_csv = file(event_filename_csv, "wb")
            events_file_csv = open(events_filename_csv, "wb")
            event_csv_writer = csv.writer(event_file_csv)
            event_csv_writer.writerow(["event_id", "area_peril_id",
                                       "intensity_bin_index", "prob"])
            events_csv_writer = csv.writer(events_file_csv)
        intensity_by_area_peril_by_event = dict()
        for event_id in range(1, num_events + 1):
            if do_csv:
                events_csv_writer.writerow([event_id])
        if do_csv:
            events_file_csv.close()
        for event_id in range(1, num_events + 1):
            if log and event_id % 100 == 0:
                print(".")
            selected_area_perils = list()
            for area_peril_id in range(1, num_area_perils_per_event + 1):
                area_peril_id = -1
                while area_peril_id == -1 or \
                        area_peril_id in selected_area_perils:
                    area_peril_id = random.randint(1, num_area_perils)
                selected_area_perils.append(area_peril_id)
                intensity = list()
                total = 0.0
                if no_intensity_uncertainty:
                    intensity_bin_index = np_random.randint(
                        1, num_intensity_bins + 1)
                    probability = 1.0
                    if do_csv:
                        event_csv_writer.writerow([
                            event_id,
                            area_peril_id,
                            intensity_bin_index,
                            probability])
                else:
                    for intensity_bin_index in range(1,
                                                     num_intensity_bins + 1):
                        value = 0.0
                        if random.uniform(0, 1) < intensity_sparseness:
                            value = random.uniform(0, 1)
                            total = total + value
                        intensity.append(value)
                    for intensity_bin_index in range(1,
                                                     num_intensity_bins + 1):
                        if intensity[intensity_bin_index - 1] == 0:
                            probability = 0
                        else:
                            probability = intensity[
                                intensity_bin_index - 1] / total
                        if do_csv:
                            event_csv_writer.writerow([
                                event_id,
                                area_peril_id,
                                intensity_bin_index,
                                probability])
        if do_csv:
            event_file_csv.close()
        if do_csv:
            damage_bin_dict_file_csv = file(damage_bin_dict_csv, "wb")
            damage_bin_dict_csv_writer = csv.writer(damage_bin_dict_file_csv)
            damage_bin_dict_csv_writer.writerow(
                ["damage_bin_index", "bin_from", "bin_to",
                 "interpolation", "interval_type"])
        bin_interval = 1.0 / (num_damage_bins - 2)
        interval_type = 1201
        for damage_bin_index in range(1, num_damage_bins + 1):
            if damage_bin_index == 1:
                bin_from = 0
                bin_to = 0
                interpolation = 0
            elif damage_bin_index == num_damage_bins:
                bin_from = 1
                bin_to = 1
                interpolation = 1
            else:
                bin_from = (damage_bin_index - 2) * bin_interval
                bin_to = (damage_bin_index - 1) * bin_interval
                interpolation = (damage_bin_index - 2 + 0.5) * bin_interval
            if do_csv:
                damage_bin_dict_csv_writer.writerow([
                    damage_bin_index, bin_from, bin_to,
                    interpolation, interval_type])
        if do_csv:
            damage_bin_dict_file_csv.close()
        t1 = time.clock()
        if log:
            print "Generated event data in {0:.2f}s".format(t1 - t0)
    except Exception, e:
        print Exception, ":", e
        exit()

    # Create directory
    static_bin_directory = "static"
    if not os.path.exists(static_bin_directory):
        os.makedirs(static_bin_directory)
    inputs_bin_directory = "input"
    if not os.path.exists(inputs_bin_directory):
        os.makedirs(inputs_bin_directory)
    data2_directory = "data2"
    if not os.path.exists(data2_directory):
        os.makedirs(data2_directory)

    # convert csv to bin
    try:
        if log:
            print "convert csv to binary"
        t0 = time.clock()
        subprocess.call(
            "damagebintobin < data/damage_bin_dict.csv > \
            static/damage_bin_dict.bin", shell=True)
        subprocess.call(
            "footprinttobin -i100 < data/footprint.csv", shell=True)
        subprocess.call(
            "occurrencetobin -P1000 < data/occurrence.csv > \
            static/occurrence.bin", shell=True)
        subprocess.call(
            "randtobin < data/random.csv > static/random.bin", shell=True)
        subprocess.call(
            "vulnerabilitytobin -d102 < data/vulnerability.csv > \
            static/vulnerability.bin", shell=True)
        subprocess.call(
            "fmpolicytctobin < data/fm_policytc.csv > \
            input/fm_policytc.bin", shell=True)
        subprocess.call(
            "fmprogrammetobin < data/fm_programme.csv > \
            input/fm_programme.bin", shell=True)
        subprocess.call(
            "fmprofiletobin < data/fm_profile.csv > \
            input/fm_profile.bin", shell=True)
        subprocess.call(
            "fmsummaryxreftobin < data/fmsummaryxref.csv > \
            input/fmsummaryxref.bin", shell=True)
        subprocess.call(
            "fmxreftobin < data/fm_xref.csv > \
            input/fm_xref.bin", shell=True)
        subprocess.call(
            "coveragetobin < data/coverages.csv > \
            input/coverages.bin", shell=True)
        subprocess.call(
            "evetobin < data/events.csv > input/events.bin", shell=True)
        subprocess.call(
            "itemtobin < data/items.csv > input/items.bin", shell=True)
        subprocess.call(
            "gulsummaryxreftobin < data/gulsummaryxref.csv > \
            input/gulsummaryxref.bin", shell=True)
        t1 = time.clock()
        if log:
            print "covert csv to bin in {0:.2f}s".format(t1 - t0)
    except Exception, e:
        print Exception, ":", e
        exit()

    # convert bin to csv for checking data
    try:
        if log:
            print "convert binary to csv"
        t0 = time.clock()
        subprocess.call(
            "damagebintocsv < static/damage_bin_dict.bin > \
            data2/damage_bin_dict2.csv", shell=True)
        subprocess.call(
            "footprinttocsv > data2/footprint2.csv", shell=True)
        subprocess.call(
            "occurrencetocsv < static/occurrence.bin > \
            data2/occurrence2.csv", shell=True)
        subprocess.call(
            "randtocsv < static/random.bin > data2/random2.csv", shell=True)
        subprocess.call(
            "vulnerabilitytocsv < static/vulnerability.bin > \
            data2/vulnerability2.csv", shell=True)
        subprocess.call(
            "fmpolicytctocsv < input/fm_policytc.bin > \
            data2/fm_policytc2.csv", shell=True)
        subprocess.call(
            "fmprogrammetocsv < input/fm_programme.bin > \
            data2/fm_programme2.csv", shell=True)
        subprocess.call(
            "fmprofiletocsv < input/fm_profile.bin > \
            data2/fm_profile2.csv", shell=True)
        subprocess.call(
            "fmsummaryxreftocsv < input/fmsummaryxref.bin > \
            data2/fmsummaryxref2.csv", shell=True)
        subprocess.call(
            "fmxreftocsv < input/fm_xref.bin > data2/fm_xref2.csv", shell=True)
        subprocess.call(
            "coveragetocsv < input/coverages.bin > \
            data2/coverages2.csv", shell=True)
        subprocess.call(
            "evetocsv < input/events.bin > data2/events2.csv", shell=True)
        subprocess.call(
            "itemtocsv < input/items.bin > data2/items2.csv", shell=True)
        subprocess.call(
            "gulsummaryxreftocsv < input/gulsummaryxref.bin > \
            data2/gulsummaryxref2.csv", shell=True)
        t1 = time.clock()
        if log:
            print "convert bin to csv in {0:.2f}s".format(t1 - t0)
    except Exception, e:
        print Exception, ":", e
        exit()

    # move file
    try:
        subprocess.call("mv footprint.bin static/", shell=True)
        subprocess.call("mv footprint.idx static/", shell=True)
    except Exception, e:
        print Exception, ":", e
        exit()

generate_test_data(
    allocrule,
    check_case,
    level_check,
    num_period,
    num_location,
    num_coverage_per_location,
    num_area_perils,
    num_vulnerabilities,
    num_events,
    num_area_perils_per_event,
    num_intensity_bins,
    no_intensity_uncertainty,
    intensity_sparseness,
    num_damage_bins,
    vulnerability_sparseness,
    data_dir,
    do_csv,
    repeatable,
    log=True)
