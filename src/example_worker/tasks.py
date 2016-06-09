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
def start_analysis(self, analysis_profile, ):
    '''
    Mock task for starting an analysis.
    '''
    logging.info("Starting task")
    self.update_state(state='STARTED')
    print analysis_profile

    failure_rate = 0.1
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

    logging.info("Done")

    return output_file