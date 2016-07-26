import os
import inspect
import time
import logging
import stat
import subprocess
from common import helpers
import sys
import json
import shutil
from threading import Thread
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
    "sample_mean_oep"]


ANALYSIS_TYPES = [
    ("summarycalc", []),
    ("eltcalc", []),
    ("leccalc", LEC_RESULT_TYPES),
    ("aalcalc", []),
    ("pltcalc", [])]


def open_process(s, dir, log_command):
    ''' Wrap subprocess.Open. Returns the Popen object. '''
    if log_command:
        log_command(s)
        p = None
    else:
        p = subprocess.Popen(s, shell=True, cwd=dir)
        logging.info('{} - process number={}'.format(s, p.pid))
    return p


def assert_is_pipe(p):
    ''' Check whether pipes used have been created'''
    assert stat.S_ISFIFO(os.stat(p).st_mode)


def waitForSubprocesses(procs):
    ''' Wait for a set of subprocesses. '''

    logging.info('Waiting for {} processes.'.format(len(procs)))
    # logging.info('still here')

    for p in procs:
        if p != None:
            if p.poll() is not None:
                logging.info('Process # {} existed with status={}'.format(p.pid, p.poll()))
            # logging.info('Process # {}: {}'.format(p.pid, status))

    logging.info('still here #2')
    for p in procs:
        if p != None:
            """
            command = "{}".format(p.pid)
            try:
                with open('/proc/{}/cmdline'.format(p.pid), 'r') as cmdF:
                    command = cmdF.read()
            except:
                pass
            """
            logging.info('waiting for process # {}'.format(p.pid))
            return_code = p.wait()
            if return_code == 0:
                logging.info(
                    'process #{} ended\n'.format(p.pid))
            else:
                raise Exception(
                    'process #{} returned error return code {}'.format(
                        p.pid, return_code))

    logging.info('Done waiting for processes.')


def outputString(
        working_directory, dir, pipe_prefix, summary, output_command, input_pipe,
        rs=[], proc_number=None):
    '''
    TODO
    Creates the output command string for running ktools.

    args:
    dir (string):
    pipe_prefix (string):   gul or fm
    summary (string):      summary id for input summary (0-9)
    output_command (string):    executable to use (leccalc, etc)
    input_pipe:
    rs (string) (optional): results parameter - relevant for leccalc only.
    procNumber (string) (optional):
    returns:
    Command string (for example 'leccalc -F < tmp/pipe > fileName.csv')
    '''

    if rs == []:
        if output_command in ['eltcalc', 'pltcalc', 'summarycalc']:
            output_pipe = "{}/{}_{}_{}{}_{}".format(
                working_directory, pipe_prefix, summary, output_command, "", proc_number)
            # os.mkfifo(output_pipe)
        if output_command == 'aalcalc':
            output_filename = "p{}.bin".format(proc_number)
            # output_filename = os.path.join(dir, file)
        else:
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
        str = 'eltcalc < {} > {}'.format(input_pipe, output_pipe)
    elif output_command == "leccalc":
        str = 'leccalc -K{} '.format(input_pipe)
        
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
        myDirShort = os.path.join('working', "{}aalSummary{}".format(pipe_prefix, summary))
        myDir = os.path.join(os.getcwd(), myDirShort)
        for d in [os.path.join(os.getcwd(), 'working'), myDir]:
            if not os.path.isdir(d):
                logging.debug('mkdir {}\n'.format(d))
                os.mkdir(d, 0777)

        str = 'aalcalc < {} > {}'.format(input_pipe, os.path.join(myDirShort, output_filename))
    elif output_command == "pltcalc":
        str = 'pltcalc < {} > {}'.format(input_pipe, output_pipe)
    elif output_command == "summarycalc":
        str = 'summarycalctocsv < {} > {}'.format(input_pipe, output_pipe)

    return str

def common_run_analysis_only(analysis_settings, number_of_processes, get_gul_and_il_cmds, log_command=None):
    '''
    Worker function for supplier OasisIM. It orchestrates data
    inputs/outputs and the spawning of subprocesses to call xtools
    across processors.
    Args:
        analysis_settings (string): the analysis settings.
        number_of_processes: the number of processes to spawn.
        get_gul_and_il_cmds (function): called to construct workflow up to and including GULs/ILs
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
    postOutputCmds = []

    for p in range(1, number_of_processes + 1):

        logging.debug('Process {} of {}'.format(p, number_of_processes))

        tee_commands = []
        output_commands = []
        gul_output = False
        il_output = False

        if 'gul_summaries' in analysis_settings and 'gul_output' in analysis_settings:
            if analysis_settings['gul_output']:
                pipe = '{}/gul{}'.format(working_directory, p)
                os.mkfifo(pipe)
                gul_output = True

        if 'il_summaries' in analysis_settings and 'il_output' in analysis_settings:
            if analysis_settings['il_output']:
                pipe = '{}/il{}'.format(working_directory, p)
                os.mkfifo(pipe)
                il_output = True

        for pipe_prefix, key, output_flag in [
                ("gul", "gul_summaries", gul_output),
                ("il", "il_summaries", il_output)
                ]:

            if output_flag:
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

                                    output_commands += [outputString(working_directory, output_directory, pipe_prefix, s['id'], a, summaryPipes[-1], proc_number=p)]

                                    if p == 1:
                                        if a in ['eltcalc', 'pltcalc', 'summarycalc']:
                                            for pp in range(1, number_of_processes + 1):
                                                output_pipe = "{}/{}_{}_{}{}_{}".format(
                                                    working_directory, pipe_prefix, s['id'], a, "", pp)
                                                os.mkfifo(output_pipe)

                                            spCmd = output_commands[-1].split('>')
                                            if len(spCmd) >= 2:
                                                postOutputCmd = "cat "
                                                for inputPipeNumber in range(1, number_of_processes + 1):
                                                    postOutputCmd += "{} ".format(spCmd[-1].replace(a + '_' + str(p), a + '_' + str(inputPipeNumber)))
                                                spCmd2 = spCmd[-1].split('/')
                                                if len(spCmd2) >= 2:
                                                    postOutputCmd += "> {}.csv".format(os.path.join(output_directory, spCmd2[-1].replace("_"+str(p),'')))
                                            # output_commands += [postOutputCmd]
                                            # postOutputCmds += [postOutputCmd]
                                            procs += [open_process(postOutputCmd, model_root, log_command)]
                                    elif p == number_of_processes and a == 'aalcalc':
                                        aalfile = "{}/{}_{}_aalcalc.csv".format(output_directory, pipe_prefix, s['id'])
                                        output_commands += ["aalsummary -K{}aalSummary{} > {}".format(pipe_prefix, s['id'], aalfile)]

                                elif isinstance(s[a], dict):
                                    if a == "leccalc" and 'lec_output' in s:
                                        if s['lec_output']:
                                            requiredRs = []
                                            for r in rs:
                                                if r in s[a]:
                                                    if s[a][r]:
                                                        requiredRs += [r]

                                            # write to file rather than use named pipe
                                            myDirShort = os.path.join('working', "{}summary{}".format(pipe_prefix, s['id']))
                                            myDir = os.path.join(model_root, myDirShort)
                                            for d in [os.path.join(model_root, 'working'), myDir]:
                                                if not os.path.isdir(d):
                                                    logging.debug('mkdir {}\n'.format(d))
                                                    os.mkdir(d, 0777)
                                            myFile = os.path.join(myDirShort, "p{}.bin".format(p))
                                            if myFile not in summaryPipes:
                                                summaryPipes += [myFile]
                                            if p == number_of_processes:   # because leccalc integrates input for all processors
                                                logging.debug('calling outputString({})\n'.format((pipe_prefix, s['id'], a, myDirShort, requiredRs)))
                                                output_commands += [outputString(working_directory, output_directory, pipe_prefix, s['id'], a, "{}summary{}".format(pipe_prefix, s['id']), requiredRs)]
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
                if 'leccalc' not in s and 'aalsummary' not in s and not s.startswith("cat "):
                    procs += [open_process(s, model_root, log_command)]

        for summaryFlag, pipe_prefix, output_flag in [("-g", "gul", gul_output), ("-f", "il", il_output)]:
            myKey = pipe_prefix+'_summaries'
            if myKey in analysis_settings and output_flag:
                summaryString = ""
                for sum in analysis_settings[myKey]:
                    myPipe = "{}/{}{}summary{}".format(working_directory, pipe_prefix, p, sum["id"])
                    assert_is_pipe(myPipe)

                    summaryString += " -{} {}".format(sum["id"], myPipe)
                myPipe = "{}/{}{}".format(working_directory, pipe_prefix, p)
                assert_is_pipe(myPipe)
                s = "summarycalc {} {} < {}".format(summaryFlag, summaryString, myPipe)
                procs += [open_process(s, model_root, log_command)]

        for s in get_gul_and_il_cmds(p, number_of_processes, analysis_settings, gul_output, il_output, log_command, working_directory):
            procs += [open_process(s, model_root, log_command)]
        
        """    
        for s in postOutputCmds:
            procs += [open_process(s, model_root, log_command)]
        """
    waitForSubprocesses(procs)

    procs = []
    # Run leccalc as it reads from a file produced by tee processors and
    # is run just once for ALL processors
    for cmds in [tee_commands, output_commands]:
        for s in cmds:
            if 'leccalc' in s or 'aalsummary' in s:
                logging.info("{}".format(s))
                procs += [open_process(s, model_root, log_command)]

    waitForSubprocesses(procs)

    # Put in error handler
    # free_shared_memory(session_id, handles, do_wind, do_stormsurge, log_command)

    end = time.time()
    logging.info("COMPLETED: {} in {}s".format(
        func_name, round(end - start, 2)))
