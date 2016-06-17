# this file implements the main framework of the Bottle calculation BE WebServices

from calcBEconfig import calcBERootDir, useCelery

if not useCelery:
    import bottle # Web server

import json
import urllib
import sys
if useCelery:
    from billiard import Process, Queue
else:
    from multiprocessing import Process, Queue
import time
import os
import re

from calcBEutils import writeBcpconnectionstringFile, getParam

class calcBEServerClass():  #bottle.Bottle
    def __init__(self):
        # super(calcBEServerClass, self).__init__()
        if not useCelery:
            self.mybottle = bottle.Bottle()
        self.calcRunning = False
        self.p = None           # worker (p)rocess
        self.verbose = False
        sys.stderr.write('calcBEServer: constructed\n')
    

    # /clean WS implementation
    def clean(self):
        if self.calcRunning:
            JSONRet = {'success' : True, 'detail' : "Calc running - can't clean"}
        else:
            sys.stderr.write('Calc not running - will clean\n')
            
            # for now will assume one clean works for all suppliers
            # clean consists of removing .bin, .csv and .tar.gz from calcBE root, 
            try:
                for d in [calcBERootDir, os.path.join(calcBERootDir, 'data'), os.path.join(calcBERootDir, 'fm'), os.path.join(calcBERootDir, 'cdf')]:
                    if os.path.isdir(d):
                        for f in os.listdir(d):
                            if f.endswith('.csv') or f.endswith('.bin') or f.endswith('.idx') or f.endswith('.tar.gz'):
                                os.remove( os.path.join(d, f) )
                JSONRet = {'success' : True, 'detail' : "Clean complete"}
            except Exception as e:
                JSONRet = {'success' : False, 'detail' : "Clean exception: {}".format(e)}
            
        sys.stderr.write("{}\n".format(JSONRet))
        return JSONRet

    
    # /hello world WS implemenation - used to test Bottle/Apache works at all
    def hello(self):
        # sys.stderr.write('got this: *{}*\n'.format(request))
    
        return "Hello from Oasis LMF Calculation Back End (CalcBE)!"
    

    # getMultiOrSingleParams is used by setupCalcProcesses() below to support both
    # single and plural params (such as 'task' and 'tasks')     
    def getMultiOrSingleParams(self, param, params, paramName):
        if params == None: 
            if param == None:
                s = 'Both {0} and {0}s params = None'.format(paramName)
                sys.stderr.write('{}\n'.format(s))
                reply = {'success' : False , 'detail' : s}
                return (reply),None,None                
            else:
                params = [param]
        else:
            sys.stderr.write('params = {}\n'.format(params))
            params = json.loads(params)
        return {'success' : True},param,params
    
    # implementation of /calc WS
    def setupCalcProcesses(self, request = None, JSONData = None):
        # sys.stderr.write('got this: *{}*\n'.format(request))

        res = self.clean()
        sys.stderr.write('Deleted old data files: {}\n'.format(res))

        os.system('export TDSVER=8.0')
        self.calcRunning = True
    
        ########################################################
        # deal with GENERIC PARAMS which apply to ANY SUPPLIER #
        ########################################################

        if (JSONData == None and request != None):
            JSONData = request.GET.get('ANALYSIS_SETTINGS_JSON', default=None)
        if JSONData == None:
            sys.stderr.write('JSONDATA not found in URL\n')
        else:
            JSONData = json.loads(JSONData)

        if 'analysis_settings' in JSONData:
            JSONData = JSONData ['analysis_settings']
        sys.stderr.write('JSONDATA = {}\n'.format(JSONData))
            
        # selection of supplier/task - will cope with either tasks or task supplied (tasks takes precedence)
            
        supplier = getParam(JSONData, 'module_supplier_id', None)
        
        ########################################################
        # get supplier's module and call it                    #
        ########################################################
        s = 'pathNotFound'
        sys.stderr.write('looking for *{}* in {}\n'.format(supplier, calcBERootDir))
        for d in os.listdir(calcBERootDir):
            fd = os.path.join(calcBERootDir, d)
            if os.path.isdir(fd):
                sys.stderr.write('found {} dir\n'.format(fd))
            else:
                sys.stderr.write('found {} NONdir\n'.format(fd))
            if os.path.isdir(fd) and supplier in d:
                s = d + '.supplierWSs'

        try:
            loadModule =  __import__(s, globals(), locals(), ['calc' ], -1 )
        except Exception as e:
            reply = { 'success' : False, 'detail' : 'module load error (1): {0}:{1}'.format(s, e) }
            sys.stderr.write("{}".format(reply['detail']))
            return json.dumps(reply)

        self.q = Queue()
        sys.stderr.write('calling PROCESS({})\n'.format(JSONData))
        JSONData['q'] = self.q
        self.p = Process(target = loadModule.calc, args=([JSONData]))

        self.p.start()
          
        if self.verbose:
            sys.stderr.write('going to loop. worker PID={}.  myPid={}\n'.format(self.p.pid, os.getpid()))
        while self.p.is_alive():
            time.sleep(1)
        
        if self.verbose:
            sys.stderr.write('out of the loop\n')
        
        # if we get this far then we have not been terminated
        
        if self.q.empty():
            retJSON = {'success' : True, 'detail' : 'Completed', 'terminated' : False}
            sys.stderr.write( 'reply is {}\n'.format(retJSON))                
            return json.dumps(retJSON)
        else:        
            reply = self.q.get_nowait()
            retJSON = json.loads(reply)
            retJSON['terminated'] = False
            reply = json.dumps(retJSON)
            sys.stderr.write( 'reply is {}\n'.format(reply))
            return reply

