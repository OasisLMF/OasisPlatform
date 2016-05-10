from celery.task import task
import time
from ConfigParser import ConfigParser
import os
import sys
import inspect
import logging

CONFIG_PARSER = ConfigParser()
CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
INI_PATH = os.path.abspath(os.path.join(CURRENT_DIRECTORY, 'Tasks.ini'))
CONFIG_PARSER.read(INI_PATH)

LOG_FILENAME = CONFIG_PARSER.get('Default', 'LOG_FILENAME')
LOG_LEVEL = CONFIG_PARSER.get('Default', 'LOG_LEVEL')
NUMERIC_LOG_LEVEL = getattr(logging, LOG_LEVEL.upper(), None)

if not isinstance(NUMERIC_LOG_LEVEL, int):
    raise ValueError('Invalid log level: %s' % LOG_LEVEL)

logging.basicConfig(
    filename=LOG_FILENAME,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

p = '/var/www/calcBE'
if not p in sys.path:
    sys.path.append(p)
from calcBEServer import calcBEServerClass
x = calcBEServerClass()

@task(bind=True)
def start_analysis(self, analysis_profile):
    '''
    Mock task for starting an analysis.
    '''
    sys.stderr.write('in start_analysis()\n')
    self.update_state(state='STARTED')
    sys.stderr.write('analysis_profile = {}\n'.format( analysis_profile))

    ret = x.setupCalcProcesses(None, analysis_profile)
    sys.stderr.write('ret = {}\n'.format(ret))
 
    return ret
