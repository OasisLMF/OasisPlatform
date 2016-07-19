import os
import inspect
import time
import logging
import stat
import subprocess
from common import helpers
import sys
import json
import tarfile
import requests
import shutil
import certifi
from threading import Thread
from model_runner_common import open_process, assert_is_pipe, waitForSubprocesses, outputString, ANALYSIS_TYPES

'''
TODO: Module description
'''

# Peril types
PERIL_WIND = "W"
PERIL_STORMSURGE = "S"

# Event sets
EVENT_SET_HISTORICAL = "H"
EVENT_SET_PROBABILISTIC = "P"

AUTH = ('howmany', 'TheAnswerMyFriendIsBlowingInTheWind')

verify_string = False
verify_mode = ""
if verify_mode == "certifi":
    verify_string = certifi.where()

if not verify_string:
    requests.packages.urllib3.disable_warnings()

def is_valid_event_set_type(event_set_type):
    return event_set_type in (model_runner_ara.EVENT_SET_HISTORICAL, 
                              model_runner_ara.EVENT_SET_PROBABILISTIC)

@helpers.oasis_log(logging.getLogger())
def do_api1(url, upx_file, verify_string, do_surge):
    ''' Call API1, which returns the area peril and vulnerability IDs'''

    api1a_url = url + 'api1a'

    logging.info("Calling API1a")
    surge_flag = 1 if do_surge else 0

    api1a_json = post(
        api1a_url,
        body={
            'number_of_cores': 0,
            'storm_surge': surge_flag,
            'upx_file': upx_file},
        files=[upx_file],
        verify=verify_string
    )

    logging.info("Response: {}".format(api1a_json))

    session_id = int(api1a_json['SessionID'])
    if session_id == -1:
        logging.exception(api1a_json)
        raise Exception(
            "API1a call failed: invalid session ID".format(session_id))

    logging.info("Polling API1b")
    start_time = time.time()
    timeout = 5000
    api1b_url = '{0}api1b/{1}'.format(url, session_id)
    t = 0
    while True:
        api1b_json = get(api1b_url, verify=verify_string)
        if api1b_json['Status'] == 'Done':
            break
        if t >= timeout:
            raise Exception("API1b timed out.")
        t = t + 1
        time.sleep(1)

    request_time = time.time() - start_time
    logging.debug(
         "API1b returned success after {0} seconds".format(request_time))

    return api1a_json


@helpers.oasis_log(logging.getLogger())
def do_api2(url, session_id, event_set_type, do_surge,
            ea_wind_filename, ea_surge_filename, verify_string):
    ''' Call API2, which does??'''

    logging.info("Calling API2")

    request_body = json.dumps({
            "SessionID": session_id,
            "W": event_set_type,
            "PerilType": PERIL_WIND})
    api2WindJSON = post(
        '{0}api2'.format(url),
        body=request_body,
        verify=verify_string)

    request_body = json.dumps({
            "SessionID": session_id,
            "W": event_set_type,
            "PerilType": PERIL_STORMSURGE}),
    if do_surge:
        api2StormSurgeJSON = post(
            '{0}api2'.format(url),
            body=request_body,
            verify=verify_string)

    logging.info("Writing chunk files")

    if do_surge:
        stormSurgeDict = dict()
        for e2 in api2StormSurgeJSON['Events']:
            stormSurgeDict[e2[u'EventID']] = e2['AreaPerilCount']

    with open(ea_wind_filename, "w") as eaWindFile,\
            open(ea_surge_filename, "w") as eaStormSurgeFile:
        eaWindFile.write(
            "EVENT_ID, AREAPERIL_COUNT, DEMAND_SURGE_FACTOR\n")
        eaStormSurgeFile.write("EVENT_ID, AREAPERIL_COUNT\n")
        for e in api2WindJSON['Events']:
            eventId = e[u'EventID']
            eaWindFile.write(
                '{0},{1},{2}\n'.format(
                    eventId, e['AreaPerilCount'], e[u'DemandSurgeFactor']))
            if do_surge:
                if eventId in stormSurgeDict:
                    eaStormSurgeFile.write('{0},{1}\n'.format(
                        eventId, stormSurgeDict[eventId]))
    return


@helpers.oasis_log(logging.getLogger())
def do_api3_vm(
        url, session_id, event_set_type, do_stormsurge,
        data_directory, vm_filename, verify_string):

    url = '{0}api3'.format(url)
    peril_type = PERIL_STORMSURGE if do_stormsurge else PERIL_WIND
    api3Body = {
        "SessionID": session_id,
        'VMData': 1,
        'W': event_set_type,
        'PerilType': peril_type,
        "Events": []}

    file = os.path.join(data_directory, vm_filename)
    post(
        url, body=json.dumps(api3Body),
        return_file=file, verify=verify_string)

    with tarfile.open(file, 'r|gz') as tar:
        tar.extractall(path=data_directory)

    return


def partitions(l, n):
    """Creates n partitions from a list l."""
    k, m = len(l) / n, len(l) % n
    return (l[i * k + min(i, m):(i + 1) * k +
            min(i + 1, m)] for i in xrange(n))


@helpers.oasis_log(logging.getLogger())
def do_api3_ef(
        number_of_partitions, request_concurrency, session_id,
        event_set_type, url, data_directory, verify_string, peril_type):

    if peril_type == PERIL_WIND:
        ea_filename = os.path.join(data_directory, 'EA_Wind_Chunk_1.csv')
        event_footprint_tar = '{0}_EventFootprintWind.tar.gz'
        event_footprint_bin = '{0}_EventFootprintWind.bin'
        ara_event_footprint_tar_filename = os.path.join(
                data_directory, '{0}_EventFootprintWind.tar.gz')
    elif peril_type == PERIL_STORMSURGE:
        ea_filename = os.path.join(data_directory, 'EA_StormSurge_Chunk_1.csv')
        event_footprint_tar = '{0}_EventFootprintStormSurge.tar.gz'
        event_footprint_bin = '{0}_EventFootprintStormSurge.bin'
        ara_event_footprint_tar_filename = os.path.join(
                data_directory, '{0}_EventFootprintStormSurge.tar.gz')
    else:
        raise Exception("Unknown peril code: {}".format(peril_type))

    event_set = set()
    with open(ea_filename, 'r') as eaf:
        eaf.readline()
        for line in eaf:
            split = line.split(',')
            event_set.add(int(split[0]))
    event_list = list(event_set)
    # Not necessary, but makes debugging easier
    event_list.sort()
    threads = list()

    url = '{0}api3'.format(url)

    event_partitions = list(partitions(event_list, number_of_partitions))
    for partition_index in range(0, number_of_partitions):
        event_partition = event_partitions[partition_index]
        logging.info('Getting EFs total events = {} of {}'.format(
                      len(event_partition), len(event_list)))
        api3Body = {"SessionID": session_id, "W": event_set_type,
                    "VMData": 0, "Events": event_partition,
                    "PerilType": peril_type}
        t = Thread(target=post, args=(
                    url,
                   [],
                    json.dumps(api3Body),
                    ara_event_footprint_tar_filename.format(partition_index),
                    verify_string))
        threads.append(t)
        t.start()
        if len(threads) == request_concurrency:
            for t in threads:
                t.join()
            threads = list()

    for t in threads:
        t.join()

    extracted_filename = os.path.join(data_directory, 'EventFootprint.bin')

    for k in range(1, number_of_partitions+1):
        tar_filename = os.path.join(
            data_directory, event_footprint_tar.format(k-1))
        event_footprint_bin_filename = os.path.join(
            data_directory, event_footprint_bin.format(k-1))
        tar = tarfile.open(tar_filename, 'r:*')
        tar.extractall(path=data_directory)
        tar.close()
        os.rename(extracted_filename, event_footprint_bin_filename)
    return


@helpers.oasis_log(logging.getLogger())
def do_api1c(url, session_id, verify_string):
    ''' Call API 1c '''

    sys.stderr.write('Calling API1c')
    get("{0}api1c/{1}".format(url, session_id), verify=verify_string)
    return


@helpers.oasis_log(logging.getLogger())
def get(url, verify=False, params={}):
    ''' Wrapper to requests.get'''

    r = requests.get(url, verify=verify, auth=AUTH, params=params)
    j = json.loads(r._content)
    logging.debug("Response = {}".format(r))
    if r.status_code == 200:
        j['success'] = True
    else:
        raise Exception(
            "Request failed URL={} Response code={}".format(
                url, r.status_code))
    return j


@helpers.oasis_log(logging.getLogger())
def post(url, files=[], body=None, return_file=None, verify=False):
    ''' Wrapper to requests.post '''

    # TODO Add retries

    upx_file = None
    if not files == []:
        head, tail = os.path.split(files[0])
        upx_file = {
            'upxfile': (
                '{fn}'.format(fn=tail),
                open(files[0], 'rb'),
                'application/text-plain')}
        files_for_post = {}
        for f in files:
            with open(f, 'r') as fd:
                content = fd.read()
            files_for_post[f] = content

    if files == []:
        if body is None:
            r = requests.post(url, verify=verify, auth=AUTH)
        else:
            r = requests.post(url, data=body, verify=verify, auth=AUTH)
    else:
        if body is None:
            r = requests.post(url, files=files_for_post,
                              verify=verify, auth=AUTH)
        else:
            r = requests.post(url, files=upx_file, data=body,
                              verify=verify, auth=AUTH)

    logging.debug("Response = {}".format(r))

    if r.status_code == 200:
        if return_file is None:
            j = json.loads(r._content)
            j['success'] = True
        else:
            with open(return_file, 'wb') as fd:
                for chunk in r.iter_content(1024):
                    fd.write(chunk)
            j = {'success': True}
    else:
        raise Exception(
            "Request failed URL={} Response code={}".format(
                url, r.status_code))
    return j



def build_get_model_cmd(session_id, partition_id, number_of_partitions, 
                        do_wind, do_stormsurge, do_demand_surge, 
                        number_of_samples, gul_threshold,
                        input_data_directory, handles):
    '''
    GetModelARA parameters:

    'S': samplesize
    's': session_id
    'B': numSamplesInBatch
    'T': _gul_threshold
    't': _fm_threshold
    'N': _Chunk_id
    'n': _nchunks
    'C': sub_nchunks
    'c': sub_chunk_id
    'K2: sub2_nchunks
    'k': sub2_Chunk_id
    'i': outputMode = itemMode;
    'd': inputDataDirectory
    'W': bWind
    'w': bStormSurge
    'M': bExtractVmToSharedMemory = true;
    'm': bExtractContentsTimeToSharedMemory = true;
    'L': bDeleteVMSharedMemory;
    'l': bDeleteCTSharedMemory
    'H': handleVMWind
    'h': handleVMStormSurge
    'J': handleCTWind
    'j': handleCTStormSurge
    'D': bDemandSurge
    'v': verbose = true
    #ifndef ARA_PRODUCTION
    'X': bCalcCDFs = true; bCalcGULs = false; bCalcFM=false;
        bOutputCDFs=true; bOutputGUL=false; bOutputFM=false;
    #endif
    'Y': bCalcCDFs = true; bCalcGULs = true; bCalcFM=false;
        bOutputCDFs=false; bOutputGUL=true; bOutputFM=false;
    #ifdef INTERNAL_FM
    'Z': bCalcCDFs = true; bCalcGULs = true; bCalcFM=true;
        bOutputCDFs=false; bOutputGUL=false; bOutputFM=true;
    #endif
    '''

    # We don't use chunks
    chunk_id = 1
    num_chunks = 1
    # We don't use sub2 chunks
    sub2_Chunk_id = 1
    num_sub2_chunks = 1

    sub_chunk_id = partition_id
    num_sub_chunks = number_of_partitions

    number_of_samples_in_batch = number_of_samples

    peril_flags = ('-w ' if do_stormsurge else '') + \
                  ('-W ' if do_wind else '') + \
                  ('-D ' if do_stormsurge else '')
    handleString = ''

    if do_wind:
        handleString = handleString + '-H{0} '.format(handles["VMWind"])
        handleString = handleString + '-J{0} '.format(handles["CTWind"])
    if do_stormsurge:
        handleString = handleString + '-h{0} '.format(handles["VMStormSurge"])
        handleString = handleString + '-j{0} '.format(handles["CTStormSurge"])

    get_model_cmd = 'getmodelara ' + \
                        '-d{} -s{} -n{} -N{} -K{} -k{} -C{} -c{} ' + \
                        '-S{} -B{} -T{} {} -Y {}'
                    
    get_model_cmd = 'getmodelara ' + \
                    "-s{} ".format(session_id) + \
                    "-n{} ".format(num_chunks) + \
                    "-N{} ".format(chunk_id) + \
                    "-K{} ".format(num_sub2_chunks) + \
                    "-k{} ".format(sub2_Chunk_id) + \
                    "-C{} ".format(num_sub_chunks) + \
                    "-c{} ".format(sub_chunk_id) + \
                    "-S{} ".format(number_of_samples) + \
                    "-B{} ".format(number_of_samples_in_batch) + \
                    "-T{} ".format(gul_threshold) + \
                    "{} ".format(peril_flags) + \
                    "{} ".format(handleString) + \
                    "-Y "

    return get_model_cmd

#@helpers.oasis_log(logging.getLogger())
def create_shared_memory(
    session_id, do_wind, do_stormsurge, log_command):
    ''' Create the shared memory segments for a session'''

    handles = dict()

    if do_wind:
        cmd = 'getmodelara -M -W -s{0} -C1'.format(session_id)
        if log_command:
            log_command(cmd)
            handles["VMWind"] = 1
        else:
            logging.info("Running getmodel command: {}".format(cmd))
            p = subprocess.Popen(cmd, shell=True)
            handles["VMWind"] = p.wait()
            
        cmd = 'getmodelara -m -W -s{0} -C1'.format(session_id)
        if log_command:
            log_command(cmd)
            handles["CTWind"] = 2
        else:
            logging.info("Running getmodel command: {}".format(cmd))
            p = subprocess.Popen(cmd, shell=True)
            handles["CTWind"] = p.wait()
            
    if do_stormsurge:
        cmd = 'getmodelara -M -w -s{0} -C1'.format(session_id)
        if log_command:
            log_command(cmd)
            handles["VMStormSurge"] = 3
        else:
            logging.info("Running getmodel command: {}".format(cmd))
            p = subprocess.Popen(cmd, shell=True)
            handles["VMStormSurge"] = p.wait()
        
        cmd = 'getmodelara -m -w -s{0} -C1'.format(session_id)
        if log_command:
            log_command(cmd)
            handles["CTStormSurge"] = 4
        else:
            logging.info("Running getmodel command: {}".format(cmd))
            p = subprocess.Popen(cmd, shell=True)
            handles["CTStormSurge"] = p.wait()

    return handles


#@helpers.oasis_log(logging.getLogger())
def free_shared_memory(session_id, handles, do_wind, do_stormsurge, log_command):
    if do_wind:
        cmd = 'getmodelara -L -W -s{} -C1 -H{}'.format(
            session_id, handles["VMWind"])
        if log_command:
            log_command(cmd)
        else:
            logging.info("Running getmodel command: {}".format(cmd))
            p = subprocess.Popen(cmd, shell=True)
            p.wait()

        cmd = 'getmodelara -l -W -s{} -C1 -J{}'.format(
            session_id, handles["CTWind"])
        if log_command:
            log_command(cmd)
        else:
            logging.info("Running getmodel command: {}".format(cmd))
            p = subprocess.Popen(cmd, shell=True)
            p.wait()

    if do_stormsurge:
        cmd = 'getmodelara -L -w -s{} -C1 -h{}'.format(
            session_id, handles["VMStormSurge"])
        if log_command:
            log_command(cmd)
        else:
            logging.info("Running getmodel command: {}".format(cmd))
            p = subprocess.Popen(cmd, shell=True)
            p.wait()

        cmd = 'getmodelara -l -w -s{} -C1 -j{}'.format(
            session_id, handles["CTStormSurge"])
        if log_command:
            log_command(cmd)
        else:
            logging.info("Running getmodel command: {}".format(cmd))
            p = subprocess.Popen(cmd, shell=True)
            p.wait()

def run_analysis(analysis_settings, number_of_partitions, log_command=None):

    url = "https://10.1.0.110:8080/oasis/"
    api3_ef_request_concurency = 1

    data_directory = os.path.join(os.getcwd(), "data")

    if not os.path.exists(data_directory):
        os.mkdir(data_directory)

    logging.debug("Data directory: {}".format(data_directory))

    model_settings = analysis_settings["model_settings"]
    session_id = model_settings["session_id"]
    do_stormsurge = bool(model_settings["peril_surge"])
    event_set_type = model_settings["event_set"]

    ea_wind_filename = os.path.join(
        data_directory, 'EA_Wind_Chunk_1.csv')
    ea_surge_filename = os.path.join(
        data_directory, 'EA_StormSurge_Chunk_1.csv')

    do_api2(url, session_id, event_set_type, do_stormsurge,
            ea_wind_filename, ea_surge_filename, verify_string)

    do_api3_vm(url, session_id, event_set_type, do_stormsurge,
               data_directory, "testVM.tar.gz", verify_string)

    do_api3_ef(number_of_partitions, api3_ef_request_concurency,
                                session_id, event_set_type, url, data_directory,
                                verify_string, PERIL_WIND)

    if do_stormsurge:
        do_api3_ef(number_of_partitions, api3_ef_request_concurency,
                                    session_id, event_set_type, url, data_directory,
                                    verify_string, PERIL_STORMSURGE)

    shutil.copyfile(
        os.path.join(os.getcwd(), "input", "coverages.bin"),
        os.path.join(os.getcwd(), "data", "coverages.bin"))

    shutil.copyfile(
        os.path.join(os.getcwd(), "input", "items.bin"),
        os.path.join(os.getcwd(), "data", "items.bin"))

    run_analysis_only(
        analysis_settings, number_of_partitions, log_command)

    do_api1c(url, session_id, verify_string)

def run_analysis_only(analysis_settings, number_of_processes, log_command=None):
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

    model_settings = analysis_settings["model_settings"]
    session_id = model_settings["session_id"]
    do_wind = bool(model_settings["peril_wind"])
    do_stormsurge = bool(model_settings["peril_surge"])
    do_demand_surge = bool(model_settings["demand_surge"])
    leakage_factor = float(model_settings["leakage_factor"])
    event_set_type = model_settings["event_set"]

    handles = create_shared_memory(session_id, do_wind, do_stormsurge, log_command)

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

                                    if p == number_of_processes:
                                        if a in ['eltcalc', 'pltcalc']:
                                            spCmd = output_commands[-1].split('>')
                                            if len(spCmd) >= 2:
                                                postOutputCmd = "cat "
                                                for inputPipeNumber in range(1, number_of_processes + 1):
                                                    postOutputCmd += "{} ".format(spCmd[-1].replace(str(p), str(inputPipeNumber)))
                                                spCmd2 = spCmd[-1].split('/')
                                                if len(spCmd2) >= 2:
                                                    postOutputCmd += "> {}.csv".format(os.path.join(output_directory, spCmd2[-1].replace("_"+str(p),'')))
                                            procs += [open_process(postOutputCmd, model_root, log_command)]
                                        elif a == 'aalcalc':
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
                if 'leccalc' not in s and 'aalsummary' not in s:
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

        # gulFlags = "-S{} ".format(analysis_settings['number_of_samples'])
        # if 'gul_threshold' in analysis_settings:
        #     gulFlags += " -L{}".format(analysis_settings['gul_threshold'])
        # if 'model_settings' in analysis_settings:
        #     if "use_random_number_file" in analysis_settings['model_settings']:
        #         if analysis_settings['model_settings']['use_random_number_file']:
        #             gulFlags += ' -r'

        partition_id = p
        number_of_partitions = number_of_processes
        input_data_directory = os.path.join(os.getcwd())
        session_id = model_settings["session_id"]
        do_wind = bool(model_settings["peril_wind"])
        do_stormsurge = bool(model_settings["peril_surge"])
        do_demand_surge = bool(model_settings["demand_surge"])
        leakage_factor = float(model_settings["leakage_factor"])
        event_set_type = model_settings["event_set"]
        number_of_samples = int(analysis_settings['number_of_samples'])
        gul_threshold = float(analysis_settings['gul_threshold'])

        get_model_ara = build_get_model_cmd(
                            session_id, partition_id, number_of_partitions, 
                            do_wind, do_stormsurge, do_demand_surge, 
                            number_of_samples, gul_threshold,
                            input_data_directory, handles)

        getModelTeePipes = []
        gulIlCmds = []
        if il_output:
            assert_is_pipe('{}/il{}'.format(working_directory, p))
            gulIlCmds += ['{} -i | fmcalc > {}/il{}'.format(get_model_ara, working_directory, p)]

        if gul_output:
            assert_is_pipe('{}/gul{}'.format(working_directory, p))
            gulIlCmds += ['{} > {}/gul{} '.format(get_model_ara, working_directory, p)]

        for s in gulIlCmds:
            procs += [open_process(s, model_root, log_command)]

    waitForSubprocesses(procs)

    procs = []
    # Run leccalc as it reads from a file produced by tee processors and
    # is run just once for ALL processors
    for s in output_commands:
        if 'leccalc' in s or 'aalsummary' in s:
            logging.info("{}".format(s))
            procs += [open_process(s, model_root, log_command)]

    waitForSubprocesses(procs)

    # Put in error handler
    # free_shared_memory(session_id, handles, do_wind, do_stormsurge, log_command)

    end = time.time()
    logging.info("COMPLETED: {} in {}s".format(
        func_name, round(end - start, 2)))
