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
'''
Mock task that creates a random results file of a specified size,
and fails with a specified probability.
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

@task(bind=True)
def start_analysis(self, analysis_profile):
    '''
    Mock task for starting an analysis.
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

        failure_rate = 0.0
        if random.uniform() < failure_rate:
            logging.exception("Random failure")
            raise Exception("Analysis failed")

        sleep_time=2
        time.sleep(sleep_time)

        # Mock results
        output_file = helpers.generate_unique_filename()
        filepath = os.path.join("/var/www/oasis/download", output_file + ".tar") 
        with open(filepath, "wb") as outfile:
            # Write 1 MB of random data
            for x in xrange(1024 * 1024):
                outfile.write(chr(randint(0,255)))
    except Exception as e:
        logging.exception("Calc BE task failed.")
        raise e

    end = time.time()
    logging.info("COMPLETED: {} in {}s".format(func_name, round(end - start,2)))

    return output_file