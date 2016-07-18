#! /usr/bin/python

import os
import sys
import json
import logging
import struct
import certifi
import requests
import argparse
import readunicedepx as upx
import inspect
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
                if av["PerilID"] == model_runner_ara.PERIL_WIND:
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
                elif av["PerilID"] == model_runner_ara.PERIL_STORMSURGE:
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
def create_session(url, upx_file, verify_string, do_stormsurge):

    api1a_json = model_runner_ara.do_api1(url, upx_file, verify_string, do_stormsurge)
    session_id = int(api1a_json['SessionID'])
    logging.debug("Session ID={}".format(session_id))

    if event_set_type not in (model_runner_ara.EVENT_SET_HISTORICAL, model_runner_ara.EVENT_SET_PROBABILISTIC):
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
parser.add_argument('-d', '--data_directory',
                    type=str,
                    default=os.getcwd(),
                    help="The data directory where the generated data will be saved.")
parser.add_argument('-v', '--verbose',
                    action='store_true',
                    help='Verbose logging.')

args = parser.parse_args()

ara_server_ip = args.ara_server_ip
upx_file = args.upx_file
analysis_settings_json = args.analysis_settings_json
do_verbose = args.verbose
data_directory = args.data_directory

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

    if not os.path.exists(analysis_settings_json):
        raise Exception(
            'Analysis settings file does not exist:{}'
            .format(analysis_settings_json))

    if not os.path.exists(data_directory):
        raise Exception(
            'Data directory does not exist:{}'
            .format(data_directory))
    data_directory = os.path.abspath(data_directory)

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

    # Parse the analysis settings file
    with open(analysis_settings_json) as file:
        analysis_settings = json.load(file)['analysis_settings']
    model_settings = analysis_settings["model_settings"]
    do_wind = bool(model_settings["peril_wind"])
    do_stormsurge = bool(model_settings["peril_surge"])
    event_set_type = model_settings["event_set"]

    session_id = create_session(url, upx_file, verify_string, do_stormsurge)
    logging.info("SessionID = {}".format(session_id))
except Exception as e:
    logging.exception("Model execution task failed.")
    os.chdir(original_directory)
    exit
