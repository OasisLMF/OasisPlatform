import os
import inspect
import time
import logging
import stat
import subprocess
'''
TODO: Module description
'''

class PerspOpts:
    GUL = 1
    FM = 2
    GULFM = 3


class AnalysisOpts:
    ELT = 1
    LEC_FULL = 2
    LEC_WHEATSHEAF = 3
    LEC_WHEATSHEAF_MEAN = 4
    LEC_SAMPLE_MEAN = 5
    AAL = 6
    PLT = 7
    ELH = 8


max_analysis_opt = AnalysisOpts.ELH


class resultsOpts:
    EBE = 1
    AGGREGATE = 2
    MAXIMUM = 3


max_result_opt = resultsOpts.MAXIMUM


# ("summarycalc", []), <- RK special case deal with in code
resultsLoc = 0
analysisLoc = 1
summaryLoc = 2


# definitions for output types and results types for each
LEC_RESULT_TYPES = [
    "return_period_file",
    "full_uncertainty_aep",
    "full_uncertainty_oep",
    "wheatsheaf_aep",
    "wheatsheaf_oep",
    "wheatsheaf_mean_aep",
    "wheatsheaf_mean_oep",
    "sample_mean_aep",
    "sample_mean_oep"
    ]


ANALYSIS_TYPES = [
    ("summarycalc", []),
    ("eltcalc", []),
    ("leccalc", LEC_RESULT_TYPES),
    ("aalcalc", []),
    ("pltcalc", [])
    ]


def open_process(s, dir, log_command):
    ''' Wrap subprocess.Open. Returns the Popen object. '''
    p = subprocess.Popen(s, shell=True, cwd=dir)
    if log_command:
        log_command(s)
    logging.debug('{} - process number={}'.format(s, p.pid))
    return p


def assert_is_pipe(p):
    ''' Check whether pipes used have been created'''
    assert stat.S_ISFIFO(os.stat(p).st_mode)
78

def waitForSubprocesses(procs):
    ''' Wait for a set of subprocesses. '''

    logging.info('Waiting for {} processes.'.format(len(procs)))

    for p in procs:
        if p.poll() is None:
            status = 'Running'
        else:
            'Exited with status {}'.format(p.poll())
        logging.debug('Process # {}: {}'.format(p.pid, status))

    for p in procs:
        #command = "{}".format(p.pid)
        #try:
        with open('/proc/{}/cmdline'.format(p.pid), 'r') as cmdF:
            command = cmdF.read()
        #except:
        #    pass
        return_code = p.wait()
        if return_code == 0:
            logging.debug(
                '{} process #{} ended\n'.format(command, p.pid))
        else:
            raise Exception(
                '{} process #{} returned error return code {}'.format(
                    command, p.pid, return_code))

    logging.info('Done waiting for processes.')


def outputString(
        dir, pipe_prefix, summary, output_command, input_pipe,
        p, rs=[], proc_number=None):
    '''
    TODO
    Creates the output command string for running ktools.

    args:
    dir (string):
    pipe_prefix (string):   gul or fm
    summary (string):      summary id for input summary (0-9)
    output_command (string):    executable to use (leccalc, etc)
    input_pipe:
    p:            number of periods for -P parameter in executables
    rs (string) (optional): results parameter - relevant for leccalc only.
    procNumber (string) (optional):
    returns:
    Command string (for example 'leccalc -F < tmp/pipe > fileName.csv')
    '''

    if rs == []:
        file = "{}_{}_{}{}_{}.csv".format(
            pipe_prefix, summary, output_command, "", proc_number)
        output_filename = os.path.join(dir, file)

    # validation
    #! TODO tidy up
    found = False
    for a, _ in ANALYSIS_TYPES:
        if a == output_command:
            found = True
    if not found:
        raise Exception("Unknown analysis type: {}".format(a))

    # generate cmd
    if output_command == "eltcalc":
        str = 'eltcalc < {} > {}'.format(input_pipe, output_filename)
    elif output_command == "leccalc":
        str = 'leccalc -P{} -K{} '.format(p, input_pipe)
        for r in rs:
            if output_command == "leccalc":
                if r not in LEC_RESULT_TYPES:
                    raise Exception('Unknown result type: {}'.format(r))

            file = "{}_{}_{}_{}.csv".format(
                pipe_prefix, summary, output_command, r)
            output_filename = os.path.join(dir, file)
            if r == "full_uncertainty_aep":
                str += '-F {} '.format(output_filename)
            elif r == "full_uncertainty_oep":
                str += '-f {} '.format(output_filename)
            elif r == "wheatsheaf_aep":
                str += '-W {} '.format(output_filename)
            elif r == "wheatsheaf_oep":
                str += '-w {} '.format(output_filename)
            elif r == "wheatsheaf_mean_aep":
                str += '-M {} '.format(output_filename)
            elif r == "wheatsheaf_mean_oep":
                str += '-m {} '.format(output_filename)
            elif r == "sample_mean_aep":
                str += '-S {} '.format(output_filename)
            elif r == "sample_mean_oep":
                str += '-s {} '.format(output_filename)
            elif r == "return_period_file":
                str += '-r '
    elif output_command == "aalcalc":
        str = 'aalcalc -P{} < {} > {}'.format(p, input_pipe, output_filename)
    elif output_command == "pltcalc":
        str = 'pltcalc -P{} < {} > {}'.format(p, input_pipe, output_filename)
    elif output_command == "summarycalc":
        str = '{} < {}'.format(output_filename, input_pipe)

    return str


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

        #! TODO Deprecated
        number_of_periods = 1000
        #! Can these be inferred from the data?
        number_of_intensity_bins = 121
        number_of_damage_bins = 102

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
                                    output_commands += [outputString(output_directory, pipe_prefix, s['id'], a, summaryPipes[-1], number_of_periods, proc_number=p)]
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
                                            logging.debug('calling outputString({})\n'.format((pipe_prefix, s['id'], a, number_of_periods, myDirShort, requiredRs)))
                                            output_commands += [outputString(output_directory, pipe_prefix, s['id'], a, "{}summary{}".format(pipe_prefix, s['id']), number_of_periods, requiredRs)]
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
        s = 'eve {} {} | getmodel -i {} -d {} > {}/getmodeltotee{}'.format(
            p, number_of_processes,
            number_of_intensity_bins, number_of_damage_bins,
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
