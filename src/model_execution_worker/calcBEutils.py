# useful functions for (re)use by the various supplier implementations
import subprocess
from calcBEconfig import useCelery, calcBERootDir

import os
import sys
import logging

def writeBcpconnectionstringFile (silentVerbose, DBIP, uid, pw, destDB):
    with open(os.path.join(calcBERootDir, 'bcpconnectionstring.txt'), 'w') as bcpF:
        s = "{};{};{};{};\n".format(DBIP, uid, pw, destDB)
        bcpF.write(s)  #    note!  IP without port number!
        if silentVerbose == 'v':
            logging.info('wrote into bcpconnectionstring.txt: {}\n'.format(s))


# turns 3 lines in the code into 1 (in many places...) 
def calcBEPopen(s, dir):

    p = subprocess.Popen(s, shell=True, cwd=dir)
    logging.info('{}\nprocess number {}\n'.format(s, p.pid))
    return p


# used to check whether pipes used have been created
import stat
def assertIsPipe(p):
    assert( stat.S_ISFIFO(os.stat(p).st_mode))


# wait for a group of subprocesses including EH and logging
def waitForSubprocesses(procs):
    logging.info( 'waiting... for {} processes.\n'.format(len(procs)))

    for p in procs:
        logging.info('process # {} is {}\n'.format(p.pid, 'running' if p.poll() == None else 'exited with status {}'.format(p.poll())))

    for p in procs:
        cmdLine = "{}".format(p.pid)
        try:
            with open('/proc/{}/cmdline'.format(p.pid), 'r') as cmdF:
                cmdLine = cmdF.read()
        except:
            pass
        r = p.wait()
        if r == 0:
            logging.info( ('{} process #{} ended\n'.format(cmdLine, p.pid)))
        else:
            logging.info( 'subprocess {} # {} returned error return code {}\n'.format(cmdLine, p.pid, r))
            # raise Exception('subprocess {} returned error return code {}'.format(cmdLine, r))
    logging.info( 'done waiting.\n')


# definitions for output types and results types for each (if any) - used together with outputString() below
lecResultTypes = ["return_period_file", "full_uncertainty_aep", "full_uncertainty_oep", "wheatsheaf_aep", "wheatsheaf_oep", "wheatsheaf_mean_aep", "wheatsheaf_mean_oep",  "sample_mean_aep", "sample_mean_oep"]

analysisTypes = [("summarycalc", []), ("eltcalc", []), ("leccalc", lecResultTypes), ("aalcalc", []), ("pltcalc", [])]


# outputString returns an output cmd string for xtools outputs
# RETURNS:      command string (for example 'leccalc -F < tmp/pipe > fileName.csv')
# Params:
# pipePrefix:   gul or fm
# summary:      summary id for input summary (0-9)
# outputcmd:    executable to use (leccalc, etc)
# p:            number of periods for -P parameter in executables
# r (optional): results parameter - relevant for leccalc only.
def outputString(dir, pipePrefix, summary, outputCmd, inputPipe, p, rs = [], procNumber = None):
    
    if rs == []:
        outputFileName = os.path.join(dir, "{}_{}_{}{}_{}.csv".format(pipePrefix, summary, outputCmd, "", procNumber))
    
    # validation
    found = False
    for a, _ in analysisTypes:
        if a == outputCmd:
            found = True
            
    if not found:
        return ''
    
    # generate cmd
    if (outputCmd == "eltcalc"):
        return  'eltcalc < {} > {}'.format(inputPipe,outputFileName)
    elif (outputCmd == "leccalc"):
        str = 'leccalc -P{} -K{} '.format(p, inputPipe)
        for r in rs:
            if outputCmd == "leccalc":
                if r not in lecResultTypes:
                    logging.info('unexpected result type {} found and ignored\n'.format(r))
            
            outputFileName = os.path.join(dir, "{}_{}_{}_{}.csv".format(pipePrefix, summary, outputCmd, r))
            if (r == "full_uncertainty_aep"):
                str +=  '-F {} '.format(outputFileName)
            elif (r == "full_uncertainty_oep"):
                str +=  '-f {} '.format(outputFileName)
            elif (r == "wheatsheaf_aep"):
                str +=  '-W {} '.format(outputFileName)
            elif (r == "wheatsheaf_oep"):
                str +=  '-w {} '.format(outputFileName)
            elif (r == "wheatsheaf_mean_aep"):
                str +=  '-M {} '.format(outputFileName)
            elif (r == "wheatsheaf_mean_oep"):
                str +=  '-m {} '.format(outputFileName)
            elif (r == "sample_mean_aep"):
                str +=  '-S {} '.format(outputFileName)
            elif (r == "sample_mean_oep"):
                str +=  '-s {} '.format(outputFileName)
            elif (r == "return_period_file"):
                str +=  '-r '
        return str
    elif (outputCmd == "aalcalc"):
        return  'aalcalc -P{} < {} > {}'.format(p, inputPipe,outputFileName)
    elif (outputCmd == "pltcalc"):
        return  'pltcalc -P{} < {} > {}'.format(p, inputPipe,outputFileName)
    elif (outputCmd == "summarycalc"):
        return '{} < {}'.format(outputFileName, inputPipe)


    

# getParam - attempt to get a value in this order:
# 1.'key' from JSON (if exists), 2. otherwise from URL, 3. otherwise defaultVal
def getParam (JSON, key, defaultVal):

    if useCelery:
        value = defaultVal
    else:
        from bottle import request
        
        value = request.GET.get(key, default=defaultVal)
    # logging.info('value={} key={}\n'.format(value,key))

    try:
        if JSON != None:
            # logging.info('json not None\n')
            value = JSON[key]
            logging.info('found {}:{} in JSON\n'.format(key, value))
    except KeyError:
        logging.info('JSONDATA={} does not contain {}\n'.format(JSON, key));
    
    return value
