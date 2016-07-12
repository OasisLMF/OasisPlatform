import inspect
import itertools
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
    ''' Generate a random filename'''
    return str(uuid.uuid4())


def escape_string_for_json(str):
    ''' Escape a string for inclusion in JSON document'''
    str = str.replace("'", "\'")
    str = str.replace('"', '\"')
    return str


def oasis_log(logger):
    def actual_oasis_log(func):
        '''
        Decorator that logs the entry, exit and execution time.
        '''
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.info("STARTED: {}".format(func.__name__))

            args_name = inspect.getargspec(func)[0]
            args_dict = dict(itertools.izip(args_name, args))

            for key, value in args_dict.iteritems():
                if key == "self":
                    continue
                logger.debug("{} == {}".format(key,value))

            for key, value in kwargs.iteritems():
                logger.debug("{} == {}".format(key,value))

            start = time.time()
            result = func(*args, **kwargs)
            end = time.time()
            logger.info(
                "COMPLETED: {} in {}s".format(
                    func_name, round(end - start,   2)))
            return result
        return wrapper
    return actual_oasis_log
