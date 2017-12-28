#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Code to generate bash script for execution from json
"""
import argparse
import io
import json
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.pardir))

from oasis_utils import (
    oasis_log_utils,
    OasisException,
)

#pylint: disable=I0011,C0111,C0103,C0301,W0603

pid_monitor_count = 0
apid_monitor_count = 0
lpid_monitor_count = 0
kpid_monitor_count = 0
command_file = ""


def print_command(cmd):
    with open(command_file, "a") as myfile:
        myfile.writelines(cmd + "\n")


def leccalc_enabled(lec_options):
    for option in lec_options["outputs"]:
        if lec_options["outputs"][option]:
            return True
    return False


def do_post_wait_processing(runtype, analysis_settings):
    global apid_monitor_count
    global lpid_monitor_count
    summary_set = 0
    if "{0}_summaries".format(runtype) not in analysis_settings:
        return

    for summary in analysis_settings["{0}_summaries".format(runtype)]:
        if "id" in summary:
            summary_set = summary["id"]
            if summary.get("aalcalc"):
                apid_monitor_count = apid_monitor_count + 1
                print_command(
                    "aalsummary -K{0}_S{1}_aalcalc > output/{0}_S{1}_aalcalc.csv & apid{2}=$!".format(
                        runtype, summary_set, apid_monitor_count))
            if summary.get("lec_output"):
                if "leccalc" in summary:
                    if leccalc_enabled(summary["leccalc"]):
                        return_period_option = ""
                        if summary["leccalc"]["return_period_file"]:
                            return_period_option = "-r"
                        cmd = "leccalc {0} -K{1}_S{2}_summaryleccalc".format(return_period_option, runtype, summary_set)
                        lpid_monitor_count = lpid_monitor_count + 1
                        for option in summary["leccalc"]["outputs"]:
                            switch = ""
                            if summary["leccalc"]["outputs"][option]:
                                if option == "full_uncertainty_aep":
                                    switch = "-F"
                                if option == "wheatsheaf_aep":
                                    switch = "-W"
                                if option == "sample_mean_aep":
                                    switch = "-S"
                                if option == "full_uncertainty_oep":
                                    switch = "-f"
                                if option == "wheatsheaf_oep":
                                    switch = "-w"
                                if option == "sample_mean_oep":
                                    switch = "-s"
                                if option == "wheatsheaf_mean_aep":
                                    switch = "-M"
                                if option == "wheatsheaf_mean_oep":
                                    switch = "-m"
                                cmd = cmd + " {0} output/{1}_S{2}_leccalc_{3}.csv".format(switch, runtype, summary_set, option)
                        cmd = cmd + "  &  lpid{0}=$!".format(lpid_monitor_count)
                        print_command(cmd)


def do_fifos(action, runtype, analysis_settings, process_id):

    summary_set = 0
    if "{0}_summaries".format(runtype) not in analysis_settings:
        return

    print_command("{0} fifo/{1}_P{2}".format(action, runtype, process_id))
    print_command("")
    for summary in analysis_settings["{0}_summaries".format(runtype)]:
        if "id" in summary:
            summary_set = summary["id"]
            print_command(
                "{0} fifo/{1}_S{2}_summary_P{3}".format(
                    action, runtype, summary_set, process_id))
            if summary.get("eltcalc"):
                print_command(
                    "{0} fifo/{1}_S{2}_summaryeltcalc_P{3}".format(
                        action, runtype, summary_set, process_id))
                print_command(
                    "{0} fifo/{1}_S{2}_eltcalc_P{3}".format(
                        action, runtype, summary_set, process_id))
            if summary.get("summarycalc"):
                print_command(
                    "{0} fifo/{1}_S{2}_summarysummarycalc_P{3}".format(
                        action, runtype, summary_set, process_id))
                print_command(
                    "{0} fifo/{1}_S{2}_summarycalc_P{3}".format(
                        action, runtype, summary_set, process_id))
            if summary.get("pltcalc"):
                print_command(
                    "{0} fifo/{1}_S{2}_summarypltcalc_P{3}".format(
                        action, runtype, summary_set, process_id))
                print_command(
                    "{0} fifo/{1}_S{2}_pltcalc_P{3}".format(
                        action, runtype, summary_set, process_id))
            if summary.get("aalcalc"):
                print_command(
                    "{0} fifo/{1}_S{2}_summaryaalcalc_P{3}".format(
                        action, runtype, summary_set, process_id))

    print_command("")


def create_workfolders(runtype, analysis_settings):

    if "{0}_summaries".format(runtype) not in analysis_settings:
        return
    for summary in analysis_settings["{0}_summaries".format(runtype)]:
        if "id" in summary:
            summary_set = summary["id"]
            if summary.get("lec_output"):
                if leccalc_enabled(summary["leccalc"]):
                    print_command(
                        "mkdir work/{0}_S{1}_summaryleccalc".format(
                            runtype, summary_set))
            if summary.get("aalcalc") is True:
                print_command("mkdir work/{0}_S{1}_aalcalc".format(runtype, summary_set))


def remove_workfolders(runtype, analysis_settings):
    print_command("rm -rf work/kat")
    if "{0}_summaries".format(runtype) not in analysis_settings:
        return
    for summary in analysis_settings["{0}_summaries".format(runtype)]:
        if "id" in summary:
            summary_set = summary["id"]
            if summary.get("lec_output"):
                if leccalc_enabled(summary["leccalc"]):
                    print_command(
                        "rm work/{0}_S{1}_summaryleccalc/*".format(
                            runtype, summary_set))
                    print_command(
                        "rmdir work/{0}_S{1}_summaryleccalc".format(
                            runtype, summary_set))
            if summary.get("aalcalc"):
                print_command(
                    "rm work/{0}_S{1}_aalcalc/*".format(
                        runtype, summary_set))
                print_command("rmdir work/{0}_S{1}_aalcalc".format(
                    runtype, summary_set))


def do_make_fifos(runtype, analysis_settings, process_id):
    do_fifos("mkfifo", runtype, analysis_settings, process_id)


def do_remove_fifos(runtype, analysis_settings, process_id):
    do_fifos("rm", runtype, analysis_settings, process_id)


def do_kats(runtype, analysis_settings, max_process_id):
    global kpid_monitor_count
    anykats = False
    if "{0}_summaries".format(runtype) not in analysis_settings:
        return anykats

    for summary in analysis_settings["{0}_summaries".format(runtype)]:
        if "id" in summary:
            summary_set = summary["id"]
            if summary.get("eltcalc"):
                anykats = True
                cmd = "kat "
                for process_id in range(1, max_process_id + 1):
                    cmd = cmd + "work/kat/{0}_S{1}_eltcalc_P{2} ".format(
                        runtype, summary_set, process_id)
                kpid_monitor_count = kpid_monitor_count + 1
                cmd = cmd + "> output/{0}_S{1}_eltcalc.csv & kpid{2}=$!".format(
                    runtype, summary_set, kpid_monitor_count)
                print_command(cmd)
            if summary.get("pltcalc"):
                anykats = True
                cmd = "kat "
                for process_id in range(1, max_process_id + 1):
                    cmd = cmd + "work/kat/{0}_S{1}_pltcalc_P{2} ".format(
                        runtype, summary_set, process_id)
                kpid_monitor_count = kpid_monitor_count + 1
                cmd = cmd + "> output/{0}_S{1}_pltcalc.csv & kpid{2}=$!".format(
                    runtype, summary_set, kpid_monitor_count)
                print_command(cmd)
            if summary.get("summarycalc"):
                anykats = True
                cmd = "kat "
                for process_id in range(1, max_process_id + 1):
                    cmd = cmd + "work/kat/{0}_S{1}_summarycalc_P{2} ".format(
                        runtype, summary_set, process_id)
                kpid_monitor_count = kpid_monitor_count + 1
                cmd = cmd + "> output/{0}_S{1}_summarycalc.csv & kpid{2}=$!".format(
                    runtype, summary_set, kpid_monitor_count)
                print_command(cmd)

    return anykats


def do_summarycalcs(runtype, analysis_settings, process_id):
    summarycalc_switch = "-g"
    if runtype == "il":
        summarycalc_switch = "-f"
    if "{0}_summaries".format(runtype) in analysis_settings:
        cmd = "summarycalc {0} ".format(summarycalc_switch)
        for summary in analysis_settings["{0}_summaries".format(runtype)]:
            if "id" in summary:
                summary_set = summary["id"]
                cmd = cmd + "-{0} fifo/{1}_S{0}_summary_P{2} ".format(
                    summary_set, runtype, process_id)
        cmd = cmd + " < fifo/{0}_P{1} &".format(runtype, process_id)
        print_command(cmd)


def do_tees(runtype, analysis_settings, process_id):
    global pid_monitor_count
    summary_set = 0
    if "{0}_summaries".format(runtype) not in analysis_settings:
        return

    for summary in analysis_settings["{0}_summaries".format(runtype)]:
        if "id" in summary:
            pid_monitor_count = pid_monitor_count + 1
            summary_set = summary["id"]
            cmd = "tee < fifo/{0}_S{1}_summary_P{2} ".format(
                runtype, summary_set, process_id)
            if summary.get("eltcalc"):
                cmd = cmd + "fifo/{0}_S{1}_summaryeltcalc_P{2} ".format(
                    runtype, summary_set, process_id)
            if summary.get("pltcalc"):
                cmd = cmd + "fifo/{0}_S{1}_summarypltcalc_P{2} ".format(
                    runtype, summary_set, process_id)
            if summary.get("summarycalc"):
                cmd = cmd + "fifo/{0}_S{1}_summarysummarycalc_P{2} ".format(
                    runtype, summary_set, process_id)
            if summary.get("aalcalc"):
                cmd = cmd + "fifo/{0}_S{1}_summaryaalcalc_P{2} ".format(
                    runtype, summary_set, process_id)
            if summary.get("lec_output") and leccalc_enabled(summary["leccalc"]):
                cmd = cmd + "work/{0}_S{1}_summaryleccalc/P{2}.bin ".format(
                    runtype, summary_set, process_id)
            cmd = cmd + " > /dev/null & pid{0}=$!".format(
                pid_monitor_count)
            print_command(cmd)


def do_any(runtype, analysis_settings, process_id):
    global pid_monitor_count

    summary_set = 0
    if "{0}_summaries".format(runtype) not in analysis_settings:
        return

    for summary in analysis_settings["{0}_summaries".format(runtype)]:
        if "id" in summary:
            summary_set = summary["id"]
            if summary.get("eltcalc"):
                cmd = "eltcalc -s"
                if process_id == 1:
                    cmd = "eltcalc"
                pid_monitor_count = pid_monitor_count + 1
                print_command(
                    "{3} < fifo/{0}_S{1}_summaryeltcalc_P{2} > work/kat/{0}_S{1}_eltcalc_P{2} & pid{4}=$!".format(
                        runtype, summary_set, process_id, cmd,pid_monitor_count))
            if summary.get("summarycalc"):
                cmd = "summarycalctocsv -s"
                if process_id == 1:
                    cmd = "summarycalctocsv"
                pid_monitor_count = pid_monitor_count + 1
                print_command(
                    "{3} < fifo/{0}_S{1}_summarysummarycalc_P{2} > work/kat/{0}_S{1}_summarycalc_P{2} & pid{4}=$!".format(
                        runtype, summary_set, process_id, cmd,pid_monitor_count))
            if summary.get("pltcalc"):
                cmd = "pltcalc -s"
                if process_id == 1:
                    cmd = "pltcalc"
                pid_monitor_count = pid_monitor_count + 1
                print_command(
                    "{3} < fifo/{0}_S{1}_summarypltcalc_P{2} > work/kat/{0}_S{1}_pltcalc_P{2} & pid{4}=$!".format(
                        runtype, summary_set, process_id, cmd,pid_monitor_count))
            if summary.get("aalcalc"):
                pid_monitor_count = pid_monitor_count + 1
                print_command(
                    "aalcalc < fifo/{0}_S{1}_summaryaalcalc_P{2} > work/{0}_S{1}_aalcalc/P{2}.bin & pid{3}=$!".format(
                        runtype, summary_set, process_id, pid_monitor_count))

        print_command("")


def do_il(analysis_settings, max_process_id):
    for process_id in range(1, max_process_id + 1):
        do_any("il", analysis_settings, process_id)

    for process_id in range(1, max_process_id + 1):
        do_tees("il", analysis_settings, process_id)

    for process_id in range(1, max_process_id + 1):
        do_summarycalcs("il", analysis_settings, process_id)

def do_gul(analysis_settings, max_process_id):
    for process_id in range(1, max_process_id + 1):
        do_any("gul", analysis_settings, process_id)

    for process_id in range(1, max_process_id + 1):
        do_tees("gul", analysis_settings, process_id)

    for process_id in range(1, max_process_id + 1):
        do_summarycalcs("gul", analysis_settings, process_id)

def do_il_make_fifo(analysis_settings, max_process_id):
    for process_id in range(1, max_process_id + 1):
        do_make_fifos("il", analysis_settings, process_id)


def do_gul_make_fifo(analysis_settings, max_process_id):
    for process_id in range(1, max_process_id + 1):
        do_make_fifos("gul", analysis_settings, process_id)


def do_il_remove_fifo(analysis_settings, max_process_id):
    for process_id in range(1, max_process_id + 1):
        do_remove_fifos("il", analysis_settings, process_id)


def do_gul_remove_fifo(analysis_settings, max_process_id):
    for process_id in range(1, max_process_id + 1):
        do_remove_fifos("gul", analysis_settings, process_id)


def do_waits(wait_variable, wait_count):
    if wait_count > 0:
        cmd = "wait "
        for pid in range(1, wait_count + 1):
            cmd = cmd + "${}{} ".format(wait_variable, pid)
        print_command(cmd)
        print_command("")


def do_pwaits():
    do_waits("pid", pid_monitor_count)


def do_awaits():
    do_waits("apid", apid_monitor_count)


def do_lwaits():
    do_waits("lpid", lpid_monitor_count)

def do_kwaits():
    do_waits("kpid", kpid_monitor_count)

def get_getmodel_cmd(
        process_id_, max_process_id,
        number_of_samples, gul_threshold,
        use_random_number_file,
        coverage_output, item_output):
    #pylint: disable=I0011, W0613
    cmd = "getmodel | gulcalc -S{0} -L{1}".format(number_of_samples, gul_threshold)

    if use_random_number_file:
        cmd = cmd + " -r"
    if coverage_output != "":
        cmd = cmd + " -c {}".format(coverage_output)
    if item_output != "":
        cmd = cmd + " -i {}".format(item_output)

    return cmd

@oasis_log_utils.oasis_log()
def genbash(
        max_process_id=None, analysis_settings=None, output_filename=None,
        get_getmodel_cmd=get_getmodel_cmd):
    """
    Generates a bash script containing ktools calculation instructions for an
    Oasis model, provided its analysis settings JSON file, the number of processes
    to use, and the path and name of the output script.
    """
    #pylint: disable=I0011, W0621
    global pid_monitor_count
    pid_monitor_count = 0
    global apid_monitor_count
    apid_monitor_count = 0
    global lpid_monitor_count
    lpid_monitor_count = 0
    global kpid_monitor_count
    kpid_monitor_count = 0

    global command_file
    command_file = output_filename

    gul_threshold = 0
    number_of_samples = 0
    use_random_number_file = False
    gul_output = False
    il_output = False

    if "gul_threshold" in analysis_settings:
        gul_threshold = analysis_settings["gul_threshold"]

    if "number_of_samples" in analysis_settings:
        number_of_samples = analysis_settings["number_of_samples"]

    if "model_settings" in analysis_settings:
        if "use_random_number_file" in analysis_settings["model_settings"]:
            if analysis_settings["model_settings"]["use_random_number_file"]:
                use_random_number_file = True

    if "gul_output" in analysis_settings:
        gul_output = analysis_settings["gul_output"]

    if "il_output" in analysis_settings:
        il_output = analysis_settings["il_output"]

    print_command("#!/bin/bash")

    print_command("")
    print_command("rm -R -f output/*")
    print_command("rm -R -f fifo/*")
    print_command("rm -R -f work/*")
    print_command("")

    print_command("mkdir work/kat")

    if gul_output:
        do_gul_make_fifo(analysis_settings, max_process_id)
        create_workfolders("gul", analysis_settings)

    print_command("")

    if il_output:
        do_il_make_fifo(analysis_settings, max_process_id)
        create_workfolders("il", analysis_settings)

    print_command("")
    print_command("# --- Do insured loss computes ---")
    print_command("")
    if il_output:
        do_il(analysis_settings, max_process_id)

    print_command("")
    print_command("# --- Do ground up loss  computes ---")
    print_command("")
    if gul_output:
        do_gul(analysis_settings, max_process_id)

    print_command("")

    for process_id in range(1, max_process_id + 1):
        if gul_output and il_output:
            getmodel_cmd = get_getmodel_cmd(
                process_id, max_process_id,
                number_of_samples, gul_threshold, use_random_number_file,
                "fifo/gul_P{}".format(process_id),
                "-")
            print_command(
                "eve {0} {1} | {2} | fmcalc > fifo/il_P{0}  &".format(
                    process_id, max_process_id, getmodel_cmd))

        else:
            #  Now the mainprocessing
            if gul_output:
                if "gul_summaries" in analysis_settings:
                    getmodel_cmd = get_getmodel_cmd(
                        process_id, max_process_id,
                        number_of_samples, gul_threshold,
                        use_random_number_file,
                        "-",
                        "")
                    print_command(
                        "eve {0} {1} | {2} > fifo/gul_P{0}  &".format(
                            process_id, max_process_id, getmodel_cmd))

            if il_output:
                if "il_summaries" in analysis_settings:
                    getmodel_cmd = get_getmodel_cmd(
                        process_id, max_process_id,
                        number_of_samples, gul_threshold,
                        use_random_number_file,
                        "",
                        "-")
                    print_command(
                        "eve {0} {1} | {2} | fmcalc > fifo/il_P{0}  &".format(
                            process_id, max_process_id, getmodel_cmd))

    print_command("")

    do_pwaits()

    print_command("")
    print_command("# --- Do insured loss kats ---")
    print_command("")
    if il_output:
        do_kats("il", analysis_settings, max_process_id)


    print_command("")
    print_command("# --- Do ground up loss kats ---")
    print_command("")
    if gul_output:
        do_kats("gul", analysis_settings, max_process_id)

    do_kwaits()

    print_command("")
    do_post_wait_processing("il", analysis_settings)
    do_post_wait_processing("gul", analysis_settings)

    do_awaits()    # waits for aalcalc
    do_lwaits()    # waits for leccalc

    if gul_output:
        do_gul_remove_fifo(analysis_settings, max_process_id)
        remove_workfolders("gul", analysis_settings)

    print_command("")

    if il_output:
        do_il_remove_fifo(analysis_settings, max_process_id)
        remove_workfolders("il", analysis_settings)


SCRIPT_RESOURCES = {
    'num_processes': {
        'arg_name': 'num_processes',
        'flag': 'n',
        'type': int,
        'help_text': 'Number of processes to use',
        'required': True
    },
    'analysis_settings_json_file_path': {
        'arg_name': 'analysis_settings_json_file_path',
        'flag': 'a',
        'type': str,
        'help_text': 'Relative or absolute path of the model analysis settings JSON file',
        'required': True
    },
    'output_file_path': {
        'arg_name': 'output_file_path',
        'flag': 'o',
        'type': str,
        'help_text': 'Relative or absolute path of the output file',
        'required': True
    }
}


def set_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filemode='w'
    )


def parse_args():
    """
    Parses script arguments and constructs and returns an arguments dict.
    """
    parser = argparse.ArgumentParser(description='Run kparse')

    di = SCRIPT_RESOURCES

    map(
        lambda res: parser.add_argument(
            '-{}'.format(di[res]['flag']),
            '--{}'.format(di[res]['arg_name']),
            type=di[res]['type'],
            required=di[res]['required'],
            help=di[res]['help_text']
        ),
        di
    )

    args = parser.parse_args()

    args_dict = vars(args)

    map(
        lambda arg: args_dict.update({arg: os.path.abspath(args_dict[arg])}) if arg.endswith('path') and args_dict[arg] else None,
        args_dict
    )

    return args_dict


if __name__ == '__main__':

    set_logging()

    logging.info('Parsing script arguments')
    args = parse_args()
    logging.info(args)

    try:
        with io.open(args['analysis_settings_json_file_path'], 'r', encoding='utf-8') as f:
            analysis_settings = json.load(f)['analysis_settings']
    except (IOError, ValueError):
        raise OasisException("Invalid analysis settings JSON file or file path: {}.".format(args['analysis_settings_json_file_path']))    

    logging.info('Analysis settings: {}'.format(analysis_settings))
    try:
        genbash(
            max_process_id=args['num_processes'],
            analysis_settings=analysis_settings,
            output_filename=args['output_file_path']
        )
    except Exception as e:
        raise OasisException(e)

    logging.info('Generated script {}'.format(args['output_file_path']))
