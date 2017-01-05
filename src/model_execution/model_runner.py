import os
import logging
import kparse
from subprocess import Popen, PIPE
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
