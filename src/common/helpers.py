import time
from functools import wraps

# Celery task status
TASK_STATUS_PENDING = "PENDING"
TASK_STATUS_RUNNING = "RUNNING"
TASK_STATUS_SUCCESS = "SUCCESS"
TASK_STATUS_FAILURE = "FAILURE"

def oasis_log(func):
    
    '''
    Decorator that logs the entry, exit and execution time.
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        print("STARTED: {}".format(func.__name__))
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print("COMPLETED: {} in {}s".format(func_name, round(end - start,2)))
        return result
    return wrapper