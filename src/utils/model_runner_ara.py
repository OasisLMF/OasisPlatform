#! /usr/bin/python

import os
import sys
import json
import logging
from multiprocessing import cpu_count
import time
import struct
import tarfile
import certifi
import requests
import argparse
import readunicedepx as upx
import inspect
from threading import Thread
import shutil

CURRENT_DIRECTORY = \
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.append(os.path.join(CURRENT_DIRECTORY, ".."))

from model_execution import model_runner_ara
from common import helpers

'''
Funcitionaity for calling ARA apis to genererate Hurloss
event footprints and vulneravility matrices.

API 1a -

API 1b -

API 2 -

API 3 -

API 1c -


The following acronyms are used:
EA - exposure area perils
EF - event footprint
VM - vulnerability matrix
'''

# Peril types
PERIL_WIND = "W"
PERIL_STORMSURGE = "S"

# Event sets
EVENT_SET_HISTORICAL = "H"
EVENT_SET_PROBABILISTIC = "P"

AUTH = ('howmany', 'TheAnswerMyFriendIsBlowingInTheWind')

@helpers.oasis_log(logging.getLogger())
def extract_tivs(upx_filename):
    ''' Extract the TIVs by location and policy from a UPX file'''
    tivs = {}
    with open(upx_filename, "r") as upx_file:
        line = upx_file.readline()
        iversionList = upx.GetUpxRecordType(line)
        iversion = iversionList[0]
        for line in upx_file:
            # logging.info("Line: {}".format(line))
            # record = upx.ParseLocationRecord(line, iversion)
            # logging.info("Record: {}".format(record))

            (retval, polid, locid, AreaScheme, StateFIPS,
             CountyFIPS, ZIP5, GeoLat, GeoLong, RiskCount,
             RepValBldg, RepValOStr, RepValCont, RepValTime,
             RVDaysCovered, ConType, ConBldg, ConOStr, OccType,
             Occ, YearBuilt, Stories, GrossArea, PerilCount, Peril,
             LimitType, Limits, Participation, DedType, Deds, territory,
             SubArea, ReinsCount, ReinsOrder, ReinsType, ReinsCID,
             ReinsField1, ReinsField2, ReinsField3, ReinsField4) \
                = upx.ParseLocationRecord(line, iversion)
            polid = polid.strip()
            locid = locid.strip()
            # logging.info("TIVs: {} {} {} {}".format(
            #     RepValBldg, RepValOStr, RepValCont, RepValTime))

            tivs[(polid, locid, 'Bldg')] = RepValBldg
            tivs[(polid, locid, 'Ostr')] = RepValOStr
            tivs[(polid, locid, 'Cont')] = RepValCont
            tivs[(polid, locid, 'Time')] = RepValTime
    return tivs


@helpers.oasis_log(logging.getLogger())
def write_exposure_files(api1a_json, tivs, item_filename, coverage_filename):
    ''' Write out the Oasis item and coverage files given an API1a response'''

    # For now groupID = itemID
    with open(item_filename, "w") as item_file,\
            open(coverage_filename, "w") as coverage_file:
        item_id = 1
        coverage_id = 1
        for loc in api1a_json['Locations']:
            for av in loc['AVs']:
                if av["PerilID"] == PERIL_WIND:
                    for covs in av['CoverageAndVulnerabilities']:
                        myTIV = tivs[(loc['PolID'], loc['LocID'], 'Bldg')]
                        coverage_file.write(
                            struct.pack('if', coverage_id+0, myTIV))
                        myTIV = tivs[(loc['PolID'], loc['LocID'], 'Ostr')]
                        coverage_file.write(
                            struct.pack('if', coverage_id+1, myTIV))
                        myTIV = tivs[(loc['PolID'], loc['LocID'], 'Cont')]
                        coverage_file.write(
                            struct.pack('if', coverage_id+2, myTIV))
                        myTIV = tivs[(loc['PolID'], loc['LocID'], 'Time')]
                        coverage_file.write(
                            struct.pack('if', coverage_id+3, myTIV))
                    for covs in av['CoverageAndVulnerabilities']:
                        myTIV = tivs[(loc['PolID'], loc['LocID'], 'Bldg')]
                        item_file.write(struct.pack(
                            'iiiii',
                            item_id+0, coverage_id+0, av['AreaPerilID'],
                            covs['VulnerabilityID'], item_id))
                        myTIV = tivs[(loc['PolID'], loc['LocID'], 'Ostr')]
                        item_file.write(struct.pack(
                            'iiiii',
                            item_id+1, coverage_id+1, av['AreaPerilID'],
                            covs['VulnerabilityID'], item_id))
                        myTIV = tivs[(loc['PolID'], loc['LocID'], 'Cont')]
                        item_file.write(struct.pack(
                            'iiiii',
                            item_id+2, coverage_id+2, av['AreaPerilID'],
                            covs['VulnerabilityID'], item_id))
                        myTIV = tivs[(loc['PolID'], loc['LocID'], 'Time')]
                        item_file.write(struct.pack(
                            'iiiii',
                            item_id+3, coverage_id+3, av['AreaPerilID'],
                            covs['VulnerabilityID'], item_id))
                elif av["PerilID"] == PERIL_STORMSURGE:
                    for covs in av['CoverageAndVulnerabilities']:
                        myTIV = tivs[(loc['PolID'], loc['LocID'], 'Bldg')]
                        item_file.write(struct.pack(
                            'iiiii',
                            item_id+4, coverage_id+0, av['AreaPerilID'],
                            covs['VulnerabilityID'], item_id))
                        myTIV = tivs[(loc['PolID'], loc['LocID'], 'Ostr')]
                        item_file.write(struct.pack(
                            'iiiii',
                            item_id+5, coverage_id+1, av['AreaPerilID'],
                            covs['VulnerabilityID'], item_id))
                        myTIV = tivs[(loc['PolID'], loc['LocID'], 'Cont')]
                        item_file.write(struct.pack(
                            'iiiii',
                            item_id+6, coverage_id+2, av['AreaPerilID'],
                            covs['VulnerabilityID'], item_id))
                        myTIV = tivs[(loc['PolID'], loc['LocID'], 'Time')]
                        item_file.write(struct.pack(
                            'iiiii',
                            item_id+7, coverage_id+3, av['AreaPerilID'],
                            covs['VulnerabilityID'], item_id))
                else:
                    raise Exception(
                        "Unknown peril code:{}".format(av["PerilID"]))

            item_id = item_id + 8
            coverage_id = coverage_id + 4
    return


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
        working_directory, vm_filename, verify_string):

    url = '{0}api3'.format(url)
    peril_type = PERIL_STORMSURGE if do_stormsurge else PERIL_WIND
    api3Body = {
        "SessionID": session_id,
        'VMData': 1,
        'W': event_set_type,
        'PerilType': peril_type,
        "Events": []}

    file = os.path.join(working_directory, vm_filename)
    post(
        url, body=json.dumps(api3Body),
        return_file=file, verify=verify_string)

    with tarfile.open(file, 'r|gz') as tar:
        tar.extractall(path=working_directory)

    return


def partitions(l, n):
    """Creates n partitions from a list l."""
    k, m = len(l) / n, len(l) % n
    return (l[i * k + min(i, m):(i + 1) * k +
            min(i + 1, m)] for i in xrange(n))


@helpers.oasis_log(logging.getLogger())
def do_api3_ef(
        number_of_partitions, request_concurrency, session_id,
        event_set_type, url, workingDir, verify_string, peril_type):

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

    extracted_filename = os.path.join(workingDir, 'EventFootprint.bin')

    for k in range(1, number_of_partitions+1):
        tar_filename = os.path.join(
            workingDir, event_footprint_tar.format(k-1))
        event_footprint_bin_filename = os.path.join(
            workingDir, event_footprint_bin.format(k-1))
        tar = tarfile.open(tar_filename, 'r:*')
        tar.extractall(path=workingDir)
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




@helpers.oasis_log(logging.getLogger())
def create_session(url, upx_file, verify_string, do_stormsurge):

    api1a_json = do_api1(url, upx_file, verify_string, do_stormsurge)
    session_id = int(api1a_json['SessionID'])
    logging.debug("Session ID={}".format(session_id))

    if event_set_type not in (EVENT_SET_HISTORICAL, EVENT_SET_PROBABILISTIC):
        raise Exception("Unknown event set type:{}".format(event_set_type))

    items_filename = os.path.join(data_directory, 'items.bin')
    coverages_filename = os.path.join(data_directory, 'coverages.bin')

    tivs = extract_tivs(upx_file)
    write_exposure_files(api1a_json, tivs, items_filename, coverages_filename)

    return session_id


parser = argparse.ArgumentParser(description='Run ARA Hurloss.')

parser.add_argument('-i', '--ara_server_ip',
                    type=str,
                    required=True,
                    help="The IP address of the ARA server.")
parser.add_argument('-u', '--upx_file',
                    type=str,
                    required=True,
                    help="The UPX file containing the exposure data.")
parser.add_argument('-a', '--analysis_settings_json',
                    type=str,
                    required=True,
                    help="The analysis settings JSON file.")
parser.add_argument('-d', '--analysis_root_directory',
                    type=str,
                    default=os.getcwd(),
                    help="The analysis root directory.")
parser.add_argument('-p', '--number_of_partitions',
                    type=int,
                    default=-1,
                    help="The number of processes to use. " +
                    "Defaults to the number of available cores.")
parser.add_argument('-n', '--number_of_ara_server_cores',
                    type=int,
                    default=12,
                    help="The number of ARA server cores. " +
                    "Defaults to 12.")
parser.add_argument('-c', '--command_debug_file',
                    type=str,
                    default='',
                    help="Debug file for the generated commands.")
parser.add_argument('-v', '--verbose',
                    action='store_true',
                    help='Verbose logging.')

args = parser.parse_args()

ara_server_ip = args.ara_server_ip
upx_file = args.upx_file
analysis_settings_json = args.analysis_settings_json
number_of_partitions = args.number_of_partitions
api3_ef_request_concurency = args.number_of_ara_server_cores
command_debug_file = args.command_debug_file
do_verbose = args.verbose
analysis_root_directory = args.analysis_root_directory

do_command_output = not command_debug_file == ''

script_root_directory = \
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))


def log_command(command):
    ''' Log a command '''
    pass


if do_verbose:
    log_level = logging.DEBUG
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
else:
    log_level = logging.INFO
    log_format = ' %(message)s'

logging.basicConfig(stream=sys.stdout, level=log_level, format=log_format)

original_directory = os.getcwd()

try:
    # Set the number of partitions
    if number_of_partitions == -1:
        number_of_partitions = cpu_count()
    if not os.path.exists(analysis_settings_json):
        raise Exception(
            'Analysis settings file does not exist:{}'
            .format(analysis_settings_json))

    if not os.path.exists(analysis_root_directory):
        raise Exception(
            'Analysis root directory does not exist:{}'
            .format(analysis_root_directory))
    analysis_root_directory = os.path.abspath(analysis_root_directory)

    if command_debug_file:
        fully_qualified_command_debug_file = \
            os.path.abspath(command_debug_file)
        with open(fully_qualified_command_debug_file, "w") as file:
            file.writelines("#!/bin/sh" + os.linesep)

        def log_command(command):
            with open(fully_qualified_command_debug_file, "a") as file:
                file.writelines(command + os.linesep)

    # Parse the analysis settings file
    with open(analysis_settings_json) as file:
        analysis_settings = json.load(file)['analysis_settings']

    data_directory = os.path.join(analysis_root_directory, "data")
    working_directory = os.path.join(analysis_root_directory, "working")

    if os.path.exists(working_directory):
        shutil.rmtree(working_directory)
    os.mkdir(working_directory)

    if os.path.exists(data_directory):
        shutil.rmtree(data_directory)
    os.mkdir(data_directory)

    url = 'https://{0}/oasis/'.format(ara_server_ip)
    upx_file = upx_file

    verify_string = False
    verify_mode = ""
    if verify_mode == "certifi":
        verify_string = certifi.where()

    if not verify_string:
        requests.packages.urllib3.disable_warnings()

    model_settings = analysis_settings["model_settings"]
    session_id = model_settings["session_id"]
    do_wind = bool(model_settings["peril_wind"])
    do_stormsurge = bool(model_settings["peril_surge"])
    do_demand_surge = bool(model_settings["demand_surge"])
    leakage_factor = float(model_settings["leakage_factor"])
    event_set_type = model_settings["event_set"]

    session_id = create_session(url, upx_file, verify_string, do_stormsurge)

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

    do_api1c(url, session_id, verify_string)

    analysis_settings['session_id'] = session_id

    shutil.copyfile(
        os.path.join(analysis_root_directory, "data", "coverages.bin"),
        os.path.join(analysis_root_directory, "input", "coverages.bin"))

    shutil.copyfile(
        os.path.join(analysis_root_directory, "data", "items.bin"),
        os.path.join(analysis_root_directory, "input", "items.bin"))

    os.chdir(analysis_root_directory)
    model_runner_ara.run_analysis(
        analysis_settings, number_of_partitions, log_command)
    os.chdir(original_directory)

except Exception as e:
    logging.exception("Model execution task failed.")
    os.chdir(original_directory)
    exit
