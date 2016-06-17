import os
import sys
import json
import shutil
import tempfile
import logging
import subprocess
from common import helpers

# from bottle import request
from ..calcBEutils import getParam, calcBEPopen, outputString, lecResultTypes, analysisTypes, assertIsPipe, waitForSubprocesses
from ..calcBEconfig import numberOfSubChunks, useCelery, calcBERootDir

if useCelery:
    from billiard import Process, Queue, cpu_count
else:
    from multiprocessing import Process, Queue, cpu_count

"""
from enum import Enum
Perspopts = Enum('Perspopt','gul fm gulfm')
analysisOpts = Enum('analysisOpts','ELT LECFull LECWheatsheaf LECWheatsheafMean LECSampleMean AAL PLT ELH')
resultsOpts = Enum('resultsOpts','EBE Aggregate Maximum')
"""
# RK:  using classes rather than Enum as the later caused various issues (a number of packages implement Enums in Python...)
# the class implementation below behaves identically to Enums

class Perspopts:
    gul=1
    fm=2
    gulfm=3
    
class analysisOpts:
    ELT=1
    LECFull=2
    LECWheatsheaf=3
    LECWheatsheafMean=4
    LECSampleMean=5
    AAL=6
    PLT=7
    ELH=8
    
maxAnalysisOpt = analysisOpts.ELH
    
class resultsOpts:
    EBE=1
    Aggregate=2
    Maximum=3

maxResultOpt = resultsOpts.Maximum

# ("summarycalc", []), <- RK special case deal with in code 

resultsLoc = 0
analysisLoc = 1
summaryLoc = 2

# this is the worker function for supplier OasisIM - it orchestrates data inputs/outputs and 
# the spawning of subprocesses to call xtools, etc across processors and cohorts

def calc (analysis_settings):
    '''
    Worker function for supplier OasisIM. It orchestrates data inputs/outputs and 
    the spawning of subprocesses to call xtools, etc across processors.
    Args:
        analysis_settings (string): the analysis settings.
    '''

    number_of_processes = cpu_count()
    working_directory = 'working'
    modelRoot = os.getcwd()
    output_dir = 'output'

    procs = []
    
    # RK: add cohort support 
    for p in range(1, number_of_processes + 1):    

        logging.info('processor {}\n'.format(p))
        
        teeCmds = []
        outputCmds = []
        
        # Deprecated
        numberOfPeriods = 1000;
        number_of_intensity_bins = 121
        number_of_damage_bins = 102
        
        if ('gul_summaries' in analysis_settings):
            pipe = '{}/gul{}'.format(working_directory, p)
            os.mkfifo(pipe)

        if ('il_summaries' in analysis_settings):
            pipe = '{}/il{}'.format(working_directory, p)
            os.mkfifo(pipe)
            
        for pipePrefix, key in [("gul", "gul_summaries"), ("il", "il_summaries")]:
            if (key in analysis_settings):
                for s in analysis_settings[key]:
                    summaryLevelPipe = '{}/{}{}summary{}'.format(working_directory, pipePrefix, p, s["id"])
                    os.mkfifo(summaryLevelPipe)

                    summaryPipes = []
                    for a, rs in analysisTypes:
                        if a in s:
                            logging.info('a = {}, s[a] = {} , type(s[a]) = {}, rs = {}\n'.format(a, s[a], type(s[a]), rs))
                            if s[a] or rs != []:   
                                logging.info('got in\n')
                                if rs == []:
                                    summaryPipes += ['{}/{}{}summary{}{}'.format(working_directory, pipePrefix, p, s["id"], a)]
                                    logging.info('new pipe: {}\n'.format(summaryPipes[-1]))
                                    os.mkfifo(summaryPipes[-1])
                                    outputCmds += [outputString(output_dir, pipePrefix, s['id'], a, summaryPipes[-1], numberOfPeriods, procNumber=p)]    
                                elif isinstance(s[a], dict):
                                    if a == "leccalc": 
                                        requiredRs = []
                                        for r in rs:
                                            if r in s[a]:
                                                if s[a][r]:  
                                                    requiredRs += [r]

                                        # write to file rather than use named pipe
                                        myDirShort = os.path.join('work', "{}summary{}".format(pipePrefix, s['id']))
                                        myDir = os.path.join(modelRoot, myDirShort)
                                        for d in [os.path.join(modelRoot, 'work'), myDir]:
                                            if not os.path.isdir(d):
                                                logging.info('mkdir {}\n'.format(d))
                                                os.mkdir(d, 0777)
                                        myFile = os.path.join(myDirShort, "p{}.bin".format(p))
                                        if myFile not in summaryPipes:
                                            summaryPipes += [myFile]
                                        if p == number_of_processes:   # because leccalc integrates input for all processors
                                            logging.info('calling outputString({})\n'.format((pipePrefix, s['id'], a, numberOfPeriods, myDirShort, requiredRs)))
                                            outputCmds += [outputString(output_dir, pipePrefix, s['id'], a, "{}summary{}".format(pipePrefix, s['id']), numberOfPeriods, requiredRs)]
                                    else:
                                        logging.info('found UNEXPECTEDLY analysis {} with results dict {}\n'.format(a, rs))
                    if len(summaryPipes) > 0:                        
                        assertIsPipe(summaryLevelPipe)
                        teeCmds += ["tee < {} ".format(summaryLevelPipe)]
                        for sp in summaryPipes[:-1]:
                            if not ".bin" in sp:
                                assertIsPipe(sp)
                            teeCmds[-1] += "{} ".format(sp)
                        if not ".bin" in summaryPipes[-1]:
                            assertIsPipe(summaryPipes[-1])
                        teeCmds[-1] += " > {}".format(summaryPipes[-1])

        # now run them in reverse order from consumers to producers
        for cmds in [teeCmds, outputCmds]:
            for s in cmds:
                if not 'leccalc' in s:
                    procs += [calcBEPopen(s, modelRoot)]

        for summaryFlag, pipePrefix in [("-g", "gul"), ("-f", "il")]:
            myKey = pipePrefix+'_summaries'
            if myKey in analysis_settings:
                summaryString = ""
                for sum in analysis_settings[myKey]:
                    myPipe = "{}/{}{}summary{}".format(working_directory, pipePrefix, p, sum["id"])
                    assertIsPipe(myPipe)

                    summaryString += " -{} {}".format(sum["id"], myPipe)
                myPipe = "{}/{}{}".format(working_directory, pipePrefix, p)
                assertIsPipe(myPipe)
                s = "summarycalc {} {} < {}".format(summaryFlag, summaryString, myPipe) 
                procs += [calcBEPopen(s, modelRoot)]

        gulFlags = "-S{} ".format(analysis_settings['number_of_samples'])
        if 'gul_threshold' in analysis_settings:
            gulFlags += " -L{}".format(analysis_settings['gul_threshold'])
        if 'model_settings' in analysis_settings:
            if "use_random_number_file" in analysis_settings['model_settings']:
                if analysis_settings['model_settings']['use_random_number_file']: 
                    gulFlags += ' -r'
                
        getModelTeePipes = []
        gulIlCmds = []
        if ('il_summaries' in analysis_settings):                
            pipe = '{}/getmodeltoil{}'.format(working_directory, p)
            getModelTeePipes += [pipe]
            os.mkfifo(pipe)
            assertIsPipe('{}/il{}'.format(working_directory, p))
            gulIlCmds += ['gulcalc {} -i - < {} | fmcalc > {}/il{}'.format(gulFlags, pipe, working_directory, p)]

        if ('gul_summaries' in analysis_settings):
            pipe = '{}/getmodeltogul{}'.format(working_directory, p)
            getModelTeePipes += [pipe]
            os.mkfifo(pipe)
            assertIsPipe('{}/gul{}'.format(working_directory, p))
            gulIlCmds += ['gulcalc {} -c - < {} > {}/gul{} '.format(gulFlags, pipe, working_directory, p)]
        
        pipe = '{}/getmodeltotee{}'.format(working_directory, p)
        os.mkfifo(pipe)
        
        assertIsPipe(pipe)
        for tp in getModelTeePipes:
            assertIsPipe(tp)
            
        getModelTee = "tee < {}".format(pipe)
        if len(getModelTeePipes) == 2:
            getModelTee += " {} > {}".format(getModelTeePipes[0], getModelTeePipes[1])
        elif len(getModelTeePipes) == 1:
            getModelTee += " > {}".format(getModelTeePipes[0])
        procs += [calcBEPopen(getModelTee, modelRoot)]

        for s in gulIlCmds:
            procs += [calcBEPopen(s, modelRoot)]
        
        assertIsPipe('{}/getmodeltotee{}'.format(working_directory, p))
        s = 'eve {} {} | getmodel -i {} -d {} > {}/getmodeltotee{}'.format(
            p, number_of_processes, 
            number_of_intensity_bins, number_of_damage_bins,
            working_directory, p) 
        procs += [calcBEPopen(s, modelRoot)]
    
    waitForSubprocesses(procs)
    
    procs = []
    # Run leccalc as it reads from a file produced by tee processors and 
    # is run just once for ALL processors
    for s in outputCmds:
        if 'leccalc' in s:
            logging.info("{}\n".format(s))
            procs += [calcBEPopen(s, modelRoot)]

    waitForSubprocesses(procs)
