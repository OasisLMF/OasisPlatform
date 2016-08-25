import os
import inspect
import time
import logging
import stat
import subprocess
from common import helpers
import re
import signal

'''
Core functions for generating the ktools commands for an analysis
settings. Some of the components, such as the getmodel
commands, may be model specific and need custom handling.
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

STATIC_DIR = 'static'
INPUT_DIR = 'input'

REQUIRED_INPUT_FILES = [
      os.path.join(INPUT_DIR, "items.bin"), 
      os.path.join(INPUT_DIR, "coverages.bin")]
      
FMCALC_INPUT_FILES = [
      os.path.join(INPUT_DIR, "fm_profile.bin"),
      os.path.join(INPUT_DIR, "fm_policytc.bin"),
      os.path.join(INPUT_DIR, "fm_programme.bin"),
      os.path.join(INPUT_DIR, "fm_xref.bin")]

IL_SUMMARYCALC_INPUT_FILES = [os.path.join(INPUT_DIR, "fmsummaryxref.bin")]
GUL_SUMMARYCALC_INPUT_FILES = [os.path.join(INPUT_DIR, "gulsummaryxref.bin")]   
LECCALC_INPUT_FILES = [os.path.join(INPUT_DIR, "returnperiods.bin")]
AAL_LEC_PLTCALC_INPUT_FILES = [os.path.join(STATIC_DIR, "occurrence.bin")]

@helpers.oasis_log(logging.getLogger())
def check_input_files(json, gul_output, il_output, supplier_specific_input_files):
    ''' Raises an Exception if any required input files are missing BEFORE the calculation starts. '''

    files_to_check = REQUIRED_INPUT_FILES + supplier_specific_input_files;
            
    if il_output:
        files_to_check += FMCALC_INPUT_FILES
        
    for o, key, files in [(gul_output, 'gul_summaries', GUL_SUMMARYCALC_INPUT_FILES), (il_output, 'il_summaries', IL_SUMMARYCALC_INPUT_FILES)]:
        if o:
            files_to_check += files
                        
            for level in json[key]:
                leccalc = False
                if 'lec_output' in level and 'leccalc' in level:
                    if level['lec_output']:
                        for r in LEC_RESULT_TYPES:
                            leccalc = leccalc or level['leccalc'][r]
                            
                plt_or_aalcalc = False
                for calc in ['pltcalc', 'aalcalc']:
                    if calc in level:
                        plt_or_aalcalc = plt_or_aalcalc or level[calc] 

                if leccalc:
                    files_to_check += LECCALC_INPUT_FILES
                            
                if leccalc or plt_or_aalcalc:
                    files_to_check += AAL_LEC_PLTCALC_INPUT_FILES

    for f in files_to_check:
        if not os.path.exists(f):
            raise Exception('Cannot find {}'.format(f))


@helpers.oasis_log(logging.getLogger())
def open_process(s, dir, log_command):
    ''' Wrap subprocess.Open. Returns the Popen object. '''
    p = None
    if log_command:
        log_command(s)
    else:
        check_pipes(s, log_command)
        s_split = s.split('|')
        for s_split_split in s_split:
            cmd = s_split_split.lstrip().split(' ')
            x = subprocess.Popen("which {}".format(cmd[0]), shell=True, cwd=dir)
            x.wait()
            if x.poll() != 0:
                msg = '{} not installed'.format(cmd[0])
                logging.error(msg)
                raise Exception(msg)

        p = subprocess.Popen(s, shell=True, cwd=dir)
        logging.info('{} - process number={}'.format(s, p.pid))

    return p


@helpers.oasis_log(logging.getLogger())
def assert_is_pipe(p):
    ''' Check whether pipes used have been created'''
    assert stat.S_ISFIFO(os.stat(p).st_mode)


def create_pipe(p, log_command):
    ''' Check whether pipes used have been created'''
    if not os.path.exists(p):
        if log_command:
            log_command("mkfifo {}".format(p))
        os.mkfifo(p)


def check_pipes(s, log_command):
    # logging.info('s = {}'.format(s))
    sps = re.split('working|\s+', s)
    # logging.info('sps = {}'.format(sps))
    for sp in sps:
        if '/' in sp:
            spsp = re.split('/', sp)
            # logging.info('spsp = {}'.format(spsp))
            for x in spsp:
                if len(x) > 0:
                    p = os.path.join('working', x)
                    # logging.info('assert pipe ***{}***'.format(p))
                    create_pipe(p, log_command)


@helpers.oasis_log(logging.getLogger())
def waitForSubprocesses(procs):
    ''' Wait for a set of subprocesses. '''

    logging.info('Waiting for {} processes.'.format(len(procs)))
    # logging.info('still here')

    for p in procs:
        if p is not None:
            if p.poll() is not None:
                logging.info('Process # {} existed with status={}'.format(p.pid, p.poll()))
            # logging.info('Process # {}: {}'.format(p.pid, status))

    logging.info('still here #2')
    for p in procs:
        if p is not None:
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


@helpers.oasis_log(logging.getLogger())
def outputString(
        working_directory, dir, pipe_prefix, summary, output_command, input_pipe,
        log_command, rs=[], proc_number=None):
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
            create_pipe(output_pipe, log_command)
        if output_command == 'aalcalc':
            output_filename = "p{}.bin".format(proc_number)
            # output_filename = os.path.join(dir, file)
        else:
            file = "{}_{}_{}{}_{}.csv".format(
                pipe_prefix, summary, output_command, "", proc_number)
            output_filename = os.path.join(dir, file)

    # validation
    # TODO tidy up
    found = False
    for a, _ in ANALYSIS_TYPES:
        if a == output_command:
            found = True
    if not found:
        raise Exception("Unknown analysis type: {}".format(a))

    # generate cmd
    if output_command == "eltcalc":
        # assert_is_pipe(output_pipe)
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
        myDirShort = os.path.join('work', "{}aalSummary{}".format(pipe_prefix, summary))
        myDir = os.path.join(os.getcwd(), myDirShort)
        for d in [os.path.join(os.getcwd(), 'working'), myDir]:
            if not os.path.isdir(d):
                logging.debug('mkdir {}\n'.format(d))
                os.mkdir(d, 0777)
        str = 'aalcalc < {} > {}'.format(input_pipe, os.path.join(myDirShort, output_filename))
    elif output_command == "pltcalc": 
        str = 'pltcalc < {} > {}'.format(input_pipe, output_pipe)
    elif output_command == "summarycalc":
        str = 'summarycalctocsv > {}'.format(input_pipe, output_pipe)

    return str


@helpers.oasis_log(logging.getLogger())
def common_run_analysis_only(
        analysis_settings, number_of_processes,
        get_gul_and_il_cmds, supplier_specific_input_files=[], log_command=None, handles=None):
    '''
    Worker function for supplier OasisIM. It orchestrates data
    inputs/outputs and the spawning of subprocesses to call xtools
    across processors.
    Args:
        analysis_settings (string): the analysis settings.
        number_of_processes: the number of processes to spawn.
        get_gul_and_il_cmds (function): called to construct workflow up to and including GULs/ILs,
        handles: the shared memory handles
        log_command: command to log process calls
    '''

    try:
        procs = []

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

        for p in range(1, number_of_processes + 1):

            postOutputCmds = []
            logging.debug('Process {} of {}'.format(p, number_of_processes))

            tee_commands = []
            output_commands = []
            gul_output = False
            il_output = False

            if 'gul_summaries' in analysis_settings and 'gul_output' in analysis_settings:
                if analysis_settings['gul_output']:
                    pipe = '{}/gul{}'.format(working_directory, p)
                    create_pipe(pipe, log_command)
                    gul_output = True

            if 'il_summaries' in analysis_settings and 'il_output' in analysis_settings:
                if analysis_settings['il_output']:
                    pipe = '{}/il{}'.format(working_directory, p)
                    create_pipe(pipe, log_command)
                    il_output = True
                    
            if p == 1:
                outputs = False
                for o, key in [(gul_output, 'gul_summaries'), (il_output, 'il_summaries')]:
                    if o:
                        for level in analysis_settings[key]:
                            for a, rs in ANALYSIS_TYPES:
                                if a in level:
                                    if level[a]:
                                        if rs == []:
                                            outputs = True 
                                        else:
                                            if 'lec_output' in level and 'leccalc' in level:
                                                if level['lec_output']:
                                                    for r in rs:
                                                        outputs = outputs or level[a][r]

                if not outputs:
                    msg = 'No outputs specified by JSON'
                    logging.error('{}\n'.format(msg))
                    raise Exception(msg)
                    
                check_input_files(analysis_settings, gul_output, il_output, supplier_specific_input_files)
                    
            for pipe_prefix, key, output_flag in [
                    ("gul", "gul_summaries", gul_output),
                    ("il", "il_summaries", il_output)
                    ]:

                if output_flag:
                    for s in analysis_settings[key]:
                        summaryLevelPipe = '{}/{}{}summary{}'.format(working_directory, pipe_prefix, p, s["id"])
                        create_pipe(summaryLevelPipe, log_command)

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
                                        create_pipe(summaryPipes[-1], log_command)

                                        output_commands += [outputString(working_directory, output_directory, pipe_prefix, s['id'], a, summaryPipes[-1], log_command, proc_number=p)]

                                        if p == 1:
                                            # logging.info('*** p == 1 ***')
                                            if a in ['eltcalc', 'pltcalc', 'summarycalc']:
                                                for pp in range(1, number_of_processes + 1):
                                                    output_pipe = "{}/{}_{}_{}{}_{}".format(
                                                        working_directory, pipe_prefix, s['id'], a, "", pp)
                                                    create_pipe(output_pipe, log_command)

                                                spCmd = output_commands[-1].split('>')
                                                if len(spCmd) >= 2:
                                                    postOutputCmd = "kat "
                                                    for inputPipeNumber in range(1, number_of_processes + 1):
                                                        myPipe = "{}".format(spCmd[-1].replace(a + '_' + str(p), a + '_' + str(inputPipeNumber))).lstrip()
                                                        assert_is_pipe(myPipe)
                                                        postOutputCmd += "{} ".format(myPipe)
                                                    spCmd2 = spCmd[-1].split('/')
                                                    if len(spCmd2) >= 2:
                                                        postOutputCmd += "> {}.csv".format(os.path.join(output_directory, re.sub("_"+str(p)+"$", '', spCmd2[-1])))
                                                # output_commands += [postOutputCmd]
                                                postOutputCmds += [postOutputCmd]
                                                # procs += [open_process(postOutputCmd, model_root, log_command)]

                                    elif isinstance(s[a], dict):
                                        if a == "leccalc" and 'lec_output' in s:
                                            if s['lec_output']:
                                                # write to file rather than use named pipe
                                                myDirShort = os.path.join('work', "{}summary{}".format(pipe_prefix, s['id']))
                                                myDir = os.path.join(model_root, myDirShort)
                                                for d in [os.path.join(model_root, 'working'), myDir]:
                                                    if not os.path.isdir(d):
                                                        logging.debug('mkdir {}\n'.format(d))
                                                        os.mkdir(d, 0777)
                                                myFile = os.path.join(myDirShort, "p{}.bin".format(p))
                                                if myFile not in summaryPipes:
                                                    summaryPipes += [myFile]
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
            for cmds in [tee_commands, postOutputCmds, output_commands]:
                for s in cmds:
                    # logging.info('found command = {}'.format(s))
                    procs += [open_process(s, model_root, log_command)]
                    
            tee_commands = []
            postOutputCmds = []
            output_commands = []

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

            for s in get_gul_and_il_cmds(p, number_of_processes, analysis_settings, gul_output, il_output, log_command, working_directory, handles):
                procs += [open_process(s, model_root, log_command)]

            """
            for s in postOutputCmds:
                procs += [open_process(s, model_root, log_command)]
            """
        waitForSubprocesses(procs)

        run_second_stage(model_root, log_command, working_directory, output_directory, gul_output, il_output, analysis_settings)

        # Put in error handler
        # free_shared_memory(session_id, handles, do_wind, do_stormsurge, log_command)

        end = time.time()
        logging.info("COMPLETED: {} in {}s".format(
            func_name, round(end - start, 2)))
    except Exception as e:
        logging.error('Exception : {}'.format(e))
        kill_all_processes(procs)
        raise e
    except:
        logging.error('Exception')
        kill_all_processes(procs)
        raise Exception


def kill_all_processes(procs):
    '''
    Error Handling (EH) function - kills all processes spawned by the worker.
    Args:
        procs: list of all processes to be killed
    '''
    count = 0
    logging.info('going to kill all worker processes')
    for p in procs:
        if p.poll() == None:
            count += 1
            try:
                os.kill(os.getpgid(p.pid), signal.SIGKILL)
            except OSError:
                pass
    logging.info('sent SIGKILL signal to {} worker processes'.format(count))
    if count > 0:
        time.sleep(1)
        count = 0
        for p in procs:
            if p.poll() == None:
                count += 1
        logging.info('one second later, {} processes out of {} still alive'.format(count, len(procs)))


def run_second_stage(model_root, log_command, working_directory, output_directory, gul_output, il_output, analysis_settings):
    '''
    Worker function running second stage executables - aalsummary and leccalc.
    Args:
        model_root: directory in which to run executables
        log_command: command to log process calls
        working_directory: path of /working
        output_directory: path of /output
        gul_output (boolean): whether GUL outputs are required
        il_output (boolean): whether IL outputs are required
        analysis_settings (string): the analysis settings.
    '''

    procs = []

    for pipe_prefix, o, key in [('gul', gul_output, 'gul_summaries'), ('il', il_output, 'il_summaries')]:
        if o:
            for s in analysis_settings[key]:
                if 'aalcalc' in s:
                    if s['aalcalc']:
                        # logging.info('*** p == number_of_processes and a == aalcalc ***')
                        aalfile = "{}/{}_{}_aalcalc.csv".format(output_directory, pipe_prefix, s['id'])
                        procs += [open_process("aalsummary -K{}aalSummary{} > {}".format(pipe_prefix, s['id'], aalfile), model_root, log_command)]
                        # logging.info('adding {}'.format(output_commands[-1]))

                if 'lec_output' in s:
                    if s['lec_output'] and 'leccalc' in s:
                        requiredRs = []
                        for r in LEC_RESULT_TYPES:
                            if r in s['leccalc']:
                                if s['leccalc'][r]:
                                    requiredRs += [r]

                        procs += [open_process(outputString(working_directory, output_directory, pipe_prefix, s['id'], 'leccalc', "{}summary{}".format(pipe_prefix, s['id']), log_command, requiredRs), model_root, log_command)]

    waitForSubprocesses(procs)

