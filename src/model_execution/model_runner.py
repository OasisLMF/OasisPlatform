import os
import logging
import kparse
from subprocess import Popen, PIPE
from common import helpers

'''
Model runner for sdtandard ktools pipeline.
'''


@helpers.oasis_log(logging.getLogger())
def get_gul_and_il_cmds(
        p, number_of_processes, analysis_settings, gul_output,
        il_output, working_directory, handles=None):
    '''
    Generate base IL and GUL commands.
    Args:
        p (int): The process number
        number_of_processes (int): The number of processes to run.
        analysis_settings (string): The analysis settings.
        gul_output (bool): True if GUL outputs are required.
        il_output (bool): True if IL outputs are required.
        log_command: Logger function for ktools commands.
        handles: NOT USED
    Returns:
        List of processes to run.
    '''

    gulOptions = "-S{} ".format(analysis_settings['number_of_samples'])
    if 'gul_threshold' in analysis_settings:
        gulOptions += " -L{}".format(analysis_settings['gul_threshold'])
    if 'model_settings' in analysis_settings:
        if "use_random_number_file" in analysis_settings['model_settings']:
            if analysis_settings['model_settings']['use_random_number_file']:
                gulOptions += ' -r'

    if 'gul_summaries' in analysis_settings and 'gul_output' in analysis_settings:
        if analysis_settings['gul_output']:
            assert_is_pipe('{}/gul{}'.format(working_directory, p))
            gulOptions = gulOptions + ' -c {}/gul{} '.format(working_directory, p)

    if 'il_summaries' in analysis_settings and 'il_output' in analysis_settings:
        if analysis_settings['il_output']:
            assert_is_pipe('{}/il{}'.format(working_directory, p))
            gulOptions = gulOptions + ' -i - | fmcalc > {}/il{}'.format(working_directory, p)

    s = 'eve {} {} | getmodel | gulcalc {}'.format(
        p, number_of_processes, gulOptions)

    return [s]


@helpers.oasis_log(logging.getLogger())
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
    cwd = os.getcwd()

    session = Popen(['bash', 'run_ktools.sh'],
        stdout=PIPE, stderr=PIPE, cwd=os.getcwd())
    stdout, stderr = session.communicate()

    if stderr:
        raise Exception("Error running ktools: "+str(stderr))