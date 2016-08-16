import os
import logging
from common import helpers
from model_runner_common import assert_is_pipe, common_run_analysis_only, INPUT_DIR, STATIC_DIR
'''
Model runner for sdtandard ktools pipeline.
'''

GENERIC_REQUIRED_INPUT_FILES = [
      os.path.join(INPUT_DIR, "events.bin"), 
      os.path.join(INPUT_DIR, "items.bin"), 
      os.path.join(STATIC_DIR, "damage_bin_dict.bin"), 
      os.path.join(STATIC_DIR, "footprint.bin"),  
      os.path.join(STATIC_DIR, "footprint.idx"), 
      os.path.join(STATIC_DIR, "vulnerability.bin"), 
      os.path.join(INPUT_DIR, "items.bin"), 
      os.path.join(STATIC_DIR, "damage_bin_dict.bin"), 
      os.path.join(STATIC_DIR, "random.bin"), 
      os.path.join(INPUT_DIR, "coverages.bin")]
      

@helpers.oasis_log(logging.getLogger())
def get_gul_and_il_cmds(
        p, number_of_processes, analysis_settings, gul_output,
        il_output, log_command, working_directory, handles=None):
    '''
    Generate base IL and GUL commands.
    Args:
        p (int): process number
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
def run_analysis(analysis_settings, number_of_processes, log_command=None):
    '''
    Worker function for supplier OasisIM. It orchestrates data
    inputs/outputs and the spawning of subprocesses to call xtools
    across processors.
    Args:
        analysis_settings (string): The analysis settings.
        number_of_processes (int): The number of processes to run.
        get_gul_and_il_cmds (function): The function to generate base
                                        ktools commands.
        log_cmmand (functiokn): Logger function for ktools commands.
    '''

    common_run_analysis_only(
        analysis_settings, number_of_processes,
        get_gul_and_il_cmds, GENERIC_REQUIRED_INPUT_FILES, log_command)
