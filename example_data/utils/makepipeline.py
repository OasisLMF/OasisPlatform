#!/usr/bin/python
# this script prints out some example pipeline commands for multiple outputs in xtools.  It is written for a single process to be extended for multiple processing later.
# the overall structure of the logic (see function doit) is;
# 1) set up temp directory for named pipes 
# 2) based on WS parameters and num processes, how many named pipes are needed? generate names for them and create them (os.mkfifo())
# 3) execute 'listening' commands for each of the named pipes in reverse order of heirarchy.  For each one, open a sub process and append to process array. Then wait for all procs to finish. this is demonstrated in multiplex_example_gul_fm_samples.py
# 4) execute command which initiates the main pipeline and sends of streams to the heirarchy of named pipes.
# There is a heirarchy of listening pipes.  Proposed heirarchy;
# Level 1 sends gul and/or fm stream to named pipes
# Level 2 takes gul and/or fm input pipes and pipes to one or more summarycalc sets 
# Level 3 tees each summarycalc set into multiple pipes depending on how many outputs there are per summarycalc set. 
        #For example, if you wanted both an OEP and AEP curve from gul summarycalc set 1, you would tee summary1 into two output pipes. 
# Level 4 takes summarycalc for a particular level and runs a single output to csv

import multiprocessing
import os, re, errno
import subprocess
import tempfile
import shutil
from enum import Enum

tmp_dir = ""
resultsfolder = ""

Perspopts = Enum('Perspopt','gul fm gulfm')
Analysisopts = Enum('Analysisopts','ELT LECFull LECWheatsheaf LECWheatsheafMean LECSampleMean AAL PLT ELH')
Resultsopts = Enum('Resultsopts','EBE Aggregate Maximum')

def init():
        #This sets up temp directory to hold the named pipes. 
        global tmp_dir
        global resultsfolder
        #purge(".","gul_results*")
        job = 1
        # randomfile = false
        tmp_dir = tempfile.mkdtemp()
        print 'The root temp directory for all named pipes:'
        print tmp_dir


def basestring():
        #This should be replaced by the supplier specific part of the pipeline which initiates the streams. In the multi-process case for OasisIM, 
        #the eve 1 1 parameters are replaced with counter and number of processes, and there is a loop over counter.
        return 'eve 1 1 | getmodel | '

def computestring(perspoption):
        #This is the compute part of the pipeline, which follows the base string. There are three fixed cases which are whether it is gul only, fm only or both gul and fm.
        #these options are WS parameter driven.  
        #For gul , only the coverage stream is output from gulcalc (-c) and sent off to a named pipe
        #For fm , only the item stream is output from gulcalc and piped straight into fmcalc. The fmcalc stream is sent to a named pipe for the processing of summarycalc.
        # For gul and fm, both coverage stream and fmcalc stream are sent off to gul and fm named pipes 
        global tmp_dir
        if (perspoption == Perspopts.gul):
                return 'gulcalc -S100 -R1000000 -c %s/gul' % (tmp_dir)
        if (perspoption == Perspopts.fm):
                return 'gulcalc -S100 -R1000000 -i - | fmcalc > %s/fm' % (tmp_dir)
        if (perspoption == Perspopts.gulfm):
                return 'gulcalc -S100 -R1000000 -c %s/gul -i - | fmcalc > %s/fm' % (tmp_dir,tmp_dir)
        fi


def teestring(fifoin,numoutputs):
        # This splits summarycalc for a given summaryset into multiple streams using tee (Level 3). The numoutputs comes from counting the number of outputs required for a given summary level for gul or fm
        global tmp_dir
        counter = 1
        str = ''
        while (counter <= numoutputs):
                str = str + ' %s/%s/output%d' %  (tmp_dir,fifoin,counter)
                counter = counter + 1
        print 'tee < %s/%s %s > /dev/null' %  (tmp_dir,fifoin,str)
        

        
def outputstring(fifoin, analysisoption, resultsoption):
        # This generates the Level 4 output command for each analysis option and results option (Level 4).
        global tmp_dir
        if (analysisoption == Analysisopts.ELT):
                return 'eltcalc < %s/%s  > %s_elt.csv' % (tmp_dir,fifoin,fifoin)
        if (analysisoption == Analysisopts.LECFull):
                str = 'leccalc -P10000 ' 
                if (resultsoption == Resultsopts.Aggregate):
                        return str + '-F < %s/%s > %s_lecfulla.csv' % (tmp_dir,fifoin,fifoin)
                if (resultsoption == Resultsopts.Maximum):
                        return str + '-f < %s/%s > %s_lecfullo.csv' % (tmp_dir,fifoin,fifoin)
                fi
        if (analysisoption == Analysisopts.LECWheatsheaf):
                str = 'leccalc -P10000 < '
                if (resultsoption == Resultsopts.Aggregate):
                        return str + '-W < %s/%s > %s_wheatsheafa.csv' % (tmp_dir,fifoin,fifoin)
                if (resultsoption == Resultsopts.Maximum):
                        return str + '-w < %s/%s > %s_wheatsheafo.csv' % (tmp_dir,fifoin,fifoin)
                fi
        if (analysisoption == Analysisopts.LECWheatsheafMean):
                str = 'leccalc -P10000 < ' 
                if (resultsoption == Resultsopts.Aggregate):
                        return str + '-M < %s/%s > %s_wheatsheafmeana.csv' % (tmp_dir,fifoin,fifoin)
                if (resultsoption == Resultsopts.Maximum):
                        return str + '-m < %s/%s > %s_wheatsheafmeano.csv' % (tmp_dir,fifoin,fifoin)
                fi
        if (analysisoption == Analysisopts.LECSampleMean):
                str = ' leccalc -P10000  < ' 
                if (resultsoption == Resultsopts.Aggregate):
                        return str + '-S < %s/%s > %s_lecsamplemeana.csv'  % (tmp_dir,fifoin,fifoin)
                if (resultsoption == Resultsopts.Maximum):
                        return str + '-s < %s/%s > %s_lecsamplemeano.csv'  % (tmp_dir,fifoin,fifoin)
                fi
        if (analysisoption == Analysisopts.AAL):
                return ' aalcalc -P10000 < %s/%s > %s_aal.csv' % (tmp_dir,fifoin,fifoin)
        if (analysisoption == Analysisopts.PLT):
                return ' pltcalc -P10000 < %s/%s > %s_plt.csv' % (tmp_dir,fifoin,fifoin)
        fi

def makefifo(name):
        #This function can be used to create the named pipes, but here we are just returning the command.
        global tmp_dir
        fifo = '%s/%s' % (tmp_dir,name)
        #os.mkfifo(fifo) 
        return fifo

def makepipes(perspoption):
        #Generates a fixed set of named pipes.  The set of summary pipes is driven by the summary set ids, and the output pipes from the number of results/analysis options per summary set, from the WS params
        print 'The named pipes:'
        if (perspoption == Perspopts.gul):
                print makefifo('gul')
                print makefifo('summary1')
                print makefifo('summary1/output1')
                print makefifo('summary2')
                print makefifo('summary2/output1')
        if (perspoption == Perspopts.fm):
                print makefifo('fm')
                print makefifo('fmsummary1')
                print makefifo('fmsummary1/output1')
                print makefifo('fmsummary2')
                print makefifo('fmsummary2/output1')               
        if (perspoption == Perspopts.gulfm):
                print makefifo('gul')
                print makefifo('summary1')
                print makefifo('summary1/output1')
                print makefifo('summary2')
                print makefifo('summary2/output1')
                print makefifo('fm')
                print makefifo('fmsummary1')
                print makefifo('fmsummary1/output1')
                print makefifo('fmsummary2')
                print makefifo('fmsummary2/output1') 


def makelevel4(perspoption):
        # Generates a fixed set of Level 4 commands. these should be driven by the analysis options from WS parameters. see  Analysisopts and Resultsopts enums.
        print 'Level 4 commands:'
        if (perspoption == Perspopts.gul):
                print outputstring('summary1/output1',Analysisopts.LECFull,Resultsopts.Aggregate)
                print outputstring('summary2/output1',Analysisopts.ELT,Resultsopts.EBE)
        if (perspoption == Perspopts.fm):
                print outputstring('fmsummary1/output1',Analysisopts.LECFull,Resultsopts.Aggregate)
                print outputstring('fmsummary2/output1',Analysisopts.ELT,Resultsopts.EBE) 
        if (perspoption == Perspopts.gulfm):
                print outputstring('summary1/output1',Analysisopts.LECFull,Resultsopts.Aggregate)
                print outputstring('summary2/output1',Analysisopts.ELT,Resultsopts.EBE) 
                print outputstring('fmsummary1/output1',Analysisopts.LECFull,Resultsopts.Aggregate)
                print outputstring('fmsummary2/output1',Analysisopts.ELT,Resultsopts.EBE) 
 

def makelevel3(perspoption):
        #Generates commands for a fixed set of summary sets. These should be driven by the summary set ids provided in the WS parameters
        print 'Level 3 commands:'
        if (perspoption == Perspopts.gul):
                print teestring('summary1',1)
                print teestring('summary2',1)
        if (perspoption == Perspopts.fm):
                print teestring('fmsummary1',1)
                print teestring('fmsummary2',1)
        if (perspoption == Perspopts.gulfm):
                print teestring('summary1',1)
                print teestring('summary2',1)
                print teestring('fmsummary1',1)
                print teestring('fmsummary2',1)

def makelevel2(perspoption):
        # This generates the listener pipelines for summarycalc (Level 2). It should be made dynamic for the required summary set ids for gul and fm from the WS parameters.
        
        print 'Level 2 commands:'
        global tmp_dir
        if (perspoption == Perspopts.gul) :
                print ' summarycalc -g -2 %s/summary2 -1 %s/summary1 < %s/gul' % (tmp_dir,tmp_dir,tmp_dir)
        if (perspoption == Perspopts.fm) :
                print ' summarycalc -f -2 %s/fmsummary2 -1 %s/fmsummary1 < %s/fm' % (tmp_dir,tmp_dir,tmp_dir)
        if (perspoption == Perspopts.gulfm) :
                print ' summarycalc -g -2 %s/summary2 -1 %s/summary1 < %s/gul' % (tmp_dir,tmp_dir,tmp_dir)
                print ' summarycalc -f -2 %s/fmsummary2 -1 %s/fmsummary1 < %s/fm' % (tmp_dir,tmp_dir,tmp_dir)


def makelevel1(perspoption):
        # This generates the initial pipeline. 
        print 'Level 1 command:'
        print basestring() + computestring(perspoption)

def fin():
        # Cleans up the tmp_dir at the end of the job
        global tmp_dir
        shutil.rmtree(tmp_dir)

def doit(option):
        init()
        makepipes(option)
        makelevel4(option)
        makelevel3(option)
        makelevel2(option)
        makelevel1(option)
        fin()

#Run one of these three commands to see the pipelines

doit(Perspopts.gul)
#doit(Perspopts.fm)
#doit(Perspopts.gulfm)


