import os
import csv
import logging
import readunicedepx as upx
from model_execution import model_runner_ara
from common import helpers
from subprocess import Popen

'''
Helper functions for creating ARA sessions and corresponding data files.
'''

def _extract_tivs(upx_filename):
    ''' Extract the TIVs by location and policy from a UPX file'''
    tivs = {}
    with open(upx_filename, "r") as upx_file:
        line = upx_file.readline()
        iversionList = upx.GetUpxRecordType(line)
        iversion = iversionList[0]
        for line in upx_file:
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

            tivs[(polid, locid, 'Bldg')] = RepValBldg
            tivs[(polid, locid, 'Ostr')] = RepValOStr
            tivs[(polid, locid, 'Cont')] = RepValCont
            tivs[(polid, locid, 'Time')] = RepValTime
    return tivs

def is_bin_file_type(file_type):
    return file_type == "bin"

def is_csv_file_type(file_type):
    return file_type == "csv"

def _write_exposure_files(api1a_json, tivs, data_directory, file_type):
    ''' Write out the Oasis item and coverage files given an API1a response'''
    
    items_csv_filename = os.path.join(data_directory, "items.csv")
    coverages_csv_filename = os.path.join(data_directory, "coverages.csv")

    if not (is_bin_file_type(file_type) or is_csv_file_type(file_type)):
        raise Exception("Unknown file type: {}".format(file_type))

    # For now groupID = itemID
    with open(items_csv_filename, "w") as items_file,\
             open(coverages_csv_filename, "w") as coverages_file:

        items_csv_writer = csv.writer(items_file)
        coverages_csv_writer = csv.writer(coverages_file)

        # Write headers
        items_csv_writer.writerow(["item_id", "coverage_id", "areaperil_id", "vulnerability_id", "group_id"])
        coverages_csv_writer.writerow(["coverage_id","tiv"])

        item_id = 1
        coverage_id = 1
        for loc in api1a_json['Locations']:
            for av in loc['AVs']:
                if av["PerilID"] == model_runner_ara.PERIL_WIND:
                    for covs in av['CoverageAndVulnerabilities']:
                        tiv = tivs[(loc['PolID'], loc['LocID'], 'Bldg')]
                        coverages_csv_writer.writerow([coverage_id + 0, tiv])
                        items_csv_writer.writerow([
                            item_id+0, coverage_id+0, av['AreaPerilID'],
                            covs['VulnerabilityID'], item_id])                        
                        
                        tiv = tivs[(loc['PolID'], loc['LocID'], 'Ostr')]
                        coverages_csv_writer.writerow([coverage_id + 1, tiv])
                        items_csv_writer.writerow([
                            item_id+1, coverage_id+1, av['AreaPerilID'],
                            covs['VulnerabilityID'], item_id])

                        tiv = tivs[(loc['PolID'], loc['LocID'], 'Cont')]
                        coverages_csv_writer.writerow([coverage_id + 2, tiv])
                        items_csv_writer.writerow([
                            item_id+2, coverage_id+2, av['AreaPerilID'],
                            covs['VulnerabilityID'], item_id])
                        
                        tiv = tivs[(loc['PolID'], loc['LocID'], 'Time')]
                        coverages_csv_writer.writerow([coverage_id + 3, tiv])
                        items_csv_writer.writerow([
                            item_id+3, coverage_id+3, av['AreaPerilID'],
                            covs['VulnerabilityID'], item_id])

                elif av["PerilID"] == model_runner_ara.PERIL_STORMSURGE:
                    for covs in av['CoverageAndVulnerabilities']:
                        tiv = tivs[(loc['PolID'], loc['LocID'], 'Bldg')]
                        items_csv_writer.writerow([
                            item_id+4, coverage_id+0, av['AreaPerilID'],
                            covs['VulnerabilityID'], item_id])
                        
                        tiv = tivs[(loc['PolID'], loc['LocID'], 'Ostr')]
                        items_csv_writer.writerow([
                            item_id+5, coverage_id+1, av['AreaPerilID'],
                            covs['VulnerabilityID'], item_id])
                        
                        tiv = tivs[(loc['PolID'], loc['LocID'], 'Cont')]
                        items_csv_writer.writerow([
                            item_id+6, coverage_id+2, av['AreaPerilID'],
                            covs['VulnerabilityID'], item_id])
                        
                        tiv = tivs[(loc['PolID'], loc['LocID'], 'Time')]
                        items_csv_writer.writerow([
                            item_id+7, coverage_id+3, av['AreaPerilID'],
                            covs['VulnerabilityID'], item_id])

                else:
                    raise Exception(
                        "Unknown peril code:{}".format(av["PerilID"]))

            item_id = item_id + 8
            coverage_id = coverage_id + 4

    items_bin_filename = os.path.join(data_directory, "items.bin")
    coverages_bin_filename = os.path.join(data_directory, "coverages.bin")

    items_to_bin_cmd = "itemtobin < {} > {}".format(items_csv_filename, items_bin_filename)
    coverages_to_bin_cmd = "coveragetobin < {} > {}".format(coverages_csv_filename, coverages_bin_filename)

    if is_bin_file_type(file_type):
        logging.debug("Cmd: {}".format(items_to_bin_cmd))
        p = Popen(items_to_bin_cmd, shell=True)
        p.wait()
        if p.returncode > 0:
            raise Exception("Items to bin conversion failed: {}".format(p.returncode))

        logging.debug("Cmd: {}".format(coverages_to_bin_cmd))
        p = Popen(coverages_to_bin_cmd, shell=True)
        p.wait()
        if p.returncode > 0:
            raise Exception("Coverages to bin conversion failed: {}".format(p.returncode))

        os.remove(items_csv_filename)
        os.remove(coverages_csv_filename)

        logging.info("Created items binary file: {}".format(items_bin_filename))
        logging.info("Created coverages binary file: {}".format(coverages_bin_filename))
    
    elif is_csv_file_type(file_type):

        logging.info("Created items CSV file: {}".format(items_csv_filename))
        logging.info("Created coverages CSV file: {}".format(coverages_csv_filename))


@helpers.oasis_log(logging.getLogger())
def create_session(url, upx_file, verify_string, do_stormsurge, data_directory, file_type="bin"):
    ''' 
    Create a session; create the associated data files in the specified 
    data directory and return the session ID.  
    '''

    api1a_json = model_runner_ara.do_api1(url, upx_file, verify_string, do_stormsurge)
    session_id = int(api1a_json['SessionID'])
    tivs = _extract_tivs(upx_file)
    _write_exposure_files(api1a_json, tivs, data_directory, file_type)

    logging.info("Created session ID={}".format(session_id))

    return session_id
