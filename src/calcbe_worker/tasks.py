from celery.task import task
import time
from ConfigParser import ConfigParser
import os
import inspect
import logging
import billiard as multiprocessing
from common import helpers
from common import data
from random import randint
from numpy import random

CALCBE_PATH = '/var/www/calcBE'
if not CALCBE_PATH in sys.path:
    sys.path.append(CALCBE_PATH)
from calcBEServer import calcBEServerClass

'''
Celery task wrapper for Oasis calculation backend (CalcBE). 
'''

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
    level=NUMERIC_LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

@task(name='oasisapi.src.calcbe_worker.tasks.start_analysis', bind=True)
def start_analysis(self, analysis_settings_json):
    '''
    Task for starting an analysis on calcBE.
    Args:
        analysis_profile_json (string): The analysis settings.
    Returns:
        (string) The location of the outputs.   
    '''
    frame = inspect.currentframe()
    func_name = inspect.getframeinfo(frame)[2]
    logging.info("STARTED: {}".format(func_name))
    args, _, _, values = inspect.getargvalues(frame)
    for i in args:
        if i == 'self': continue
        logging.info("{}={}".format(i, values[i]))
    start = time.time()

    try:
        self.update_state(state=helpers.TASK_STATUS_RUNNING)
        calcbe_server = calcBEServerClass()
        outputs_location = calcbe_server.setupCalcProcesses(None, analysis_settings_json)
        logging.info("Outputs location = {}".format(outputs_location))
    except Exception as e:
        logging.exception("Calc BE task failed.")
        raise e

    end = time.time()
    logging.info("COMPLETED: {} in {}s".format(func_name, round(end - start,2)))
 
    return outputs_location