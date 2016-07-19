import os
import inspect
import time
import logging
import stat
import subprocess
from model_runner_common import open_process, assert_is_pipe, waitForSubprocesses, outputString, ANALYSIS_TYPES
'''
TODO: Module description
'''

def run_analysis(analysis_settings, number_of_processes, log_command=None):
    '''
    Worker function for supplier OasisIM. It orchestrates data
    inputs/outputs and the spawning of subprocesses to call xtools
    across processors.
    Args:
        analysis_settings (string): the analysis settings.
        number_of_processes: the number of processes to spawn.
    '''
    
    frame = inspect.currentframe()
    func_name = inspect.getframeinfo(frame)[2]
    logging.info("STARTED: {}".format(func_name))
    args, _, _, values = inspect.getargvalues(frame)
    for i in args:
        if i == 'self':
            continue
        logging.debug("{}={}".format(i, values[i]))
    start = time.time()

    working_directory = 'working'
    model_root = os.getcwd()
    output_directory = 'output'

    procs = []

    for p in range(1, number_of_processes + 1):

        logging.debug('Process {} of {}'.format(p, number_of_processes))

        tee_commands = []
        output_commands = []

        if 'gul_summaries' in analysis_settings:
            pipe = '{}/gul{}'.format(working_directory, p)
            os.mkfifo(pipe)

        if 'il_summaries' in analysis_settings:
            pipe = '{}/il{}'.format(working_directory, p)
            os.mkfifo(pipe)

        for pipe_prefix, key in [
                ("gul", "gul_summaries"),
                ("il", "il_summaries")
                ]:

            if key in analysis_settings:
                for s in analysis_settings[key]:
                    summaryLevelPipe = '{}/{}{}summary{}'.format(working_directory, pipe_prefix, p, s["id"])
                    os.mkfifo(summaryLevelPipe)

                    summaryPipes = []
                    for a, rs in ANALYSIS_TYPES:
                        if a in s:
                            logging.debug(
                                'a = {}, s[a] = {} , type(s[a]) = {}, rs = {}\n'.format(
                                    a, s[a], type(s[a]), rs))
                            if s[a] or rs != []:
                                if rs == []:
                                    summaryPipes += ['{}/{}{}summary{}{}'.format(working_directory, pipe_prefix, p, s["id"], a)]
                                    logging.debug('new pipe: {}\n'.format(summaryPipes[-1]))
                                    os.mkfifo(summaryPipes[-1])
                                    output_commands += [outputString(output_directory, pipe_prefix, s['id'], a, summaryPipes[-1], proc_number=p)]
                                elif isinstance(s[a], dict):
                                    if a == "leccalc":
                                        requiredRs = []
                                        for r in rs:
                                            if r in s[a]:
                                                if s[a][r]:
                                                    requiredRs += [r]

                                        # write to file rather than use named pipe
                                        myDirShort = os.path.join('work', "{}summary{}".format(pipe_prefix, s['id']))
                                        myDir = os.path.join(model_root, myDirShort)
                                        for d in [os.path.join(model_root, 'work'), myDir]:
                                            if not os.path.isdir(d):
                                                logging.debug('mkdir {}\n'.format(d))
                                                os.mkdir(d, 0777)
                                        myFile = os.path.join(myDirShort, "p{}.bin".format(p))
                                        if myFile not in summaryPipes:
                                            summaryPipes += [myFile]
                                        if p == number_of_processes:   # because leccalc integrates input for all processors
                                            logging.debug('calling outputString({})\n'.format((pipe_prefix, s['id'], a, myDirShort, requiredRs)))
                                            output_commands += [outputString(output_directory, pipe_prefix, s['id'], a, "{}summary{}".format(pipe_prefix, s['id']), requiredRs)]
                                    else:
                                        # TODO what is this? Should it be an error?
                                        logging.info('Unexpectedly found analysis {} with results dict {}\n'.format(a, rs))
                    if len(summaryPipes) > 0:
                        assert_is_pipe(summaryLevelPipe)
                        tee_commands += ["tee < {} ".format(summaryLevelPipe)]
                        for sp in summaryPipes[:-1]:
                            if ".bin" not in sp:
                                assert_is_pipe(sp)
                            tee_commands[-1] += "{} ".format(sp)
                        if ".bin" not in summaryPipes[-1]:
                            assert_is_pipe(summaryPipes[-1])
                        tee_commands[-1] += " > {}".format(summaryPipes[-1])

        # now run them in reverse order from consumers to producers
        for cmds in [tee_commands, output_commands]:
            for s in cmds:
                if 'leccalc' not in s:
                    procs += [open_process(s, model_root, log_command)]

        for summaryFlag, pipe_prefix in [("-g", "gul"), ("-f", "il")]:
            myKey = pipe_prefix+'_summaries'
            if myKey in analysis_settings:
                summaryString = ""
                for sum in analysis_settings[myKey]:
                    myPipe = "{}/{}{}summary{}".format(working_directory, pipe_prefix, p, sum["id"])
                    assert_is_pipe(myPipe)

                    summaryString += " -{} {}".format(sum["id"], myPipe)
                myPipe = "{}/{}{}".format(working_directory, pipe_prefix, p)
                assert_is_pipe(myPipe)
                s = "summarycalc {} {} < {}".format(summaryFlag, summaryString, myPipe)
                procs += [open_process(s, model_root, log_command)]

        gulFlags = "-S{} ".format(analysis_settings['number_of_samples'])
        if 'gul_threshold' in analysis_settings:
            gulFlags += " -L{}".format(analysis_settings['gul_threshold'])
        if 'model_settings' in analysis_settings:
            if "use_random_number_file" in analysis_settings['model_settings']:
                if analysis_settings['model_settings']['use_random_number_file']:
                    gulFlags += ' -r'

        getModelTeePipes = []
        gulIlCmds = []
        if 'il_summaries' in analysis_settings:
            pipe = '{}/getmodeltoil{}'.format(working_directory, p)
            getModelTeePipes += [pipe]
            os.mkfifo(pipe)
            assert_is_pipe('{}/il{}'.format(working_directory, p))
            gulIlCmds += ['gulcalc {} -i - < {} | fmcalc > {}/il{}'.format(gulFlags, pipe, working_directory, p)]

        if 'gul_summaries' in analysis_settings:
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
        procs += [open_process(getModelTee, model_root, log_command)]

        for s in gulIlCmds:
            procs += [open_process(s, model_root, log_command)]

        assert_is_pipe('{}/getmodeltotee{}'.format(working_directory, p))
        s = 'eve {} {} | getmodel > {}/getmodeltotee{}'.format(
            p, number_of_processes,
            working_directory, p)
        procs += [open_process(s, model_root, log_command)]

    waitForSubprocesses(procs)

    procs = []
    # Run leccalc as it reads from a file produced by tee processors and
    # is run just once for ALL processors
    for s in output_commands:
        if 'leccalc' in s:
            logging.info("{}".format(s))
            procs += [open_process(s, model_root, log_command)]

    waitForSubprocesses(procs)

    end = time.time()
    logging.info("COMPLETED: {} in {}s".format(
        func_name, round(end - start, 2)))
