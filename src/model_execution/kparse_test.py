#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
        Test harness for kparse.py
"""

from __future__ import print_function

import getopt
import inspect
import json
import os
import sys

from pprint import pprint

cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.abspath(os.path.join(cwd, os.pardir))
sys.path.insert(0, parent_dir)

import oasis_utils.kparse as kparse

#pylint: disable=I0011,C0111

def usage():
    print("-a analysis settings")
    print("-p No of Processors")

def main(argv):
    processor_count = 1
    analysis_filename = ""
    output_file = "output.sh"
    try:
        opts, _ = getopt.getopt(argv, "p:a:o:", ["help", "grammar="])

    except getopt.GetoptError:
        usage()
        sys.exit(-1)

    for opt, arg in opts:
        if opt in "-p":
            processor_count = int(arg)
        elif opt in "-a":
            analysis_filename = arg
        elif opt in "-o":
            output_file = arg

    with open(analysis_filename) as data_file:
        analysis_data = json.load(data_file)

    try:
    	os.remove(output_file)
    except OSError:
    	pass

    # pprint(analysis_data)
    kparse.genbash(processor_count, analysis_data["analysis_settings"], output_file)

if __name__ == "__main__":
    main(sys.argv[1:])
