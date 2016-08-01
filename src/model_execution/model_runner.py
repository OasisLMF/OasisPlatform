import os
from model_runner_common import assert_is_pipe, common_run_analysis_only
'''
Model runner for sdtandard ktools pipeline.
'''


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

    gulFlags = "-S{} ".format(analysis_settings['number_of_samples'])
    if 'gul_threshold' in analysis_settings:
        gulFlags += " -L{}".format(analysis_settings['gul_threshold'])
    if 'model_settings' in analysis_settings:
        if "use_random_number_file" in analysis_settings['model_settings']:
            if analysis_settings['model_settings']['use_random_number_file']:
                gulFlags += ' -r'

    getModelTeePipes = []
    gulIlCmds = []
    if 'il_summaries' in analysis_settings and 'il_output' in analysis_settings:
        if analysis_settings['il_output']:
            pipe = '{}/getmodeltoil{}'.format(working_directory, p)
            getModelTeePipes += [pipe]
            os.mkfifo(pipe)
            assert_is_pipe('{}/il{}'.format(working_directory, p))
            gulIlCmds += ['gulcalc {} -i - < {} | fmcalc > {}/il{}'.format(gulFlags, pipe, working_directory, p)]

    if 'gul_summaries' in analysis_settings and 'gul_output' in analysis_settings:
        if analysis_settings['gul_output']:
            pipe = '{}/getmodeltogul{}'.format(working_directory, p)
            getModelTeePipes += [pipe]
            os.mkfifo(pipe)
            assert_is_pipe('{}/gul{}'.format(working_directory, p))
            gulIlCmds += ['gulcalc {} -c - < {} > {}/gul{} '.format(gulFlags, pipe, working_directory, p)]

    pipe = '{}/getmodeltotee{}'.format(working_directory, p)
    os.mkfifo(pipe)

    assert_is_pipe(pipe)
    for tp in getModelTeePipes:
        assert_is_pipe(tp)

    getModelTee = "tee < {}".format(pipe)
    if len(getModelTeePipes) == 2:
        getModelTee += " {} > {}".format(getModelTeePipes[0], getModelTeePipes[1])
    elif len(getModelTeePipes) == 1:
        getModelTee += " > {}".format(getModelTeePipes[0])
    # procs += [open_process(getModelTee, model_root, log_command)]

    assert_is_pipe('{}/getmodeltotee{}'.format(working_directory, p))
    s = 'eve {} {} | getmodel > {}/getmodeltotee{}'.format(
        p, number_of_processes,
        working_directory, p)

    return [getModelTee] + gulIlCmds + [s]


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
        get_gul_and_il_cmds, log_command)
