import inspect
import time
import uuid
from functools import wraps

# Celery task status
TASK_STATUS_PENDING = "PENDING"
TASK_STATUS_RUNNING = "RUNNING"
TASK_STATUS_SUCCESS = "SUCCESS"
TASK_STATUS_FAILURE = "FAILURE"

# HTTP codes
HTTP_RESPONSE_OK = 200
HTTP_RESPONSE_BAD_REQUEST = 400
HTTP_RESPONSE_RESOURCE_NOT_FOUND = 404
HTTP_RESPONSE_INTERNAL_SERVER_ERROR = 500

def generate_unique_filename():
    return str(uuid.uuid4())

def oasis_log(logger):
    def actual_oasis_log(func):
        '''
        Decorator that logs the entry, exit and execution time.
        '''
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.info("STARTED: {}".format(func.__name__))
            args, _, _, values = inspect.getargvalues(inspect.currentframe())
            for i in args:
                logger.info("{}={}").format(i, values[i])
            start = time.time()
                
            result = func(*args, **kwargs)
                
            end = time.time()
            logger.info("COMPLETED: {} in {}s".format(func_name, round(end - start,2)))
            return result
        return wrapper
    return actual_oasis_log
