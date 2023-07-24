import importlib
import logging
from functools import wraps

from django.conf import settings

logger = logging.getLogger('root')


def requires_sql_reader(func):
    """
        Certain endpoints are only available if Dask or a SQL compatible reader is configured. Endpoints
        will not be showing in swagger or available if not.
    """
    @wraps(func)
    def _func(*args, **kwargs):
        return func(*args, **kwargs)

    try:
        module, klass = settings.DEFAULT_READER_ENGINE.rsplit('.', 1)
        reader_module = importlib.import_module(module)
        reader_class = getattr(reader_module, klass)

        if hasattr(reader_class, 'apply_sql'):
            return _func
    except (ModuleNotFoundError, AttributeError):
        logger.warning('Incorrectly configured DEFAULT_READER_ENGINE, SQL endpoints disabled.')
    return None
