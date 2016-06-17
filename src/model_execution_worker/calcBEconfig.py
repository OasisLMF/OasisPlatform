#################################################################################
# Config file ... values here may be modified during installation               # 
#                 and later if required.                                        #
#################################################################################

#################################################################################
# IP address:port - required for ARA server (where supplier = "ARA")            #
#################################################################################

IP = '10.1.0.2:8000'    # write IP and port (if anay) using this format:  '1.2.3.4:10'

#################################################################################
# useFreebcp - uses freebcp if True ; bcp if false                              #
#################################################################################

useFreebcp = False

#################################################################################
# outputsByFreebcp - uses freebcp for outputs regardless of value of useFreebcp #
# this is required BECAUSE bcp only accepts .bin input but outputcalc only      #
# produces .csv output.                                                         #
#################################################################################

outputsByFreebcp = True     

#################################################################################
# Root directory - should match Apache config                                   #
#################################################################################

calcBERootDir = "/var/www/calcBE"

#################################################################################
# parameters that depend on local HW                                            #
#################################################################################

defaultNumberOfSubChunks = 1

numberOfARAServerCores = 12

numberOfSamplesInBatch = 10000

numberOfCohorts = 10    # used to split run across all processes into a number of 'cohorts'

import multiprocessing
numberOfSubChunks = multiprocessing.cpu_count() * numberOfCohorts

remoteLocal = "remote"      # only use local if we are on the same machine as the ARA server or if we can mount the appropriate directory on the ARA Server

useCelery = True
