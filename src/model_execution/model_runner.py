import inspect
import os
import sys
import logging

from subprocess import (
    Popen,
    PIPE,
)

cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.abspath(os.path.join(cwd, os.pardir))
sys.path.insert(0, parent_dir)

import oasis_utils.kparse as kparse

from oasis_utils import oasis_log_utils 

'''
Model runner for standard ktools pipeline.
'''


@oasis_log_utils.oasis_log()
def run_analysis(analysis_settings, number_of_processes):
    '''
    Worker function for supplier OasisIM. It orchestrates data
    inputs/outputs and the spawning of subprocesses to call xtools
    across processors.
    Args:
        analysis_settings (string): The analysis settings.
        number_of_processes (int): The number of processes to run.
    '''

    kparse.genbash(number_of_processes, analysis_settings, "run_ktools.sh")

    session = Popen(['bash', 'run_ktools.sh'],
                    stdout=PIPE, stderr=PIPE,
                    cwd=os.getcwd())
    stdout, stderr = session.communicate()

    if stderr:
        raise Exception("Error running ktools: "+str(stderr))
