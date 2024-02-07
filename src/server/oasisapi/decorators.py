import importlib
import logging
from functools import wraps

from django.conf import settings
from django.http import HttpResponseBadRequest
from rest_framework.response import Response

logger = logging.getLogger('root')


def requires_sql_reader(func):
    """
        Certain endpoints are only available if Dask or a SQL compatible reader is configured. Endpoints
        will not be showing in swagger or available if not.
    """
    @wraps(func)
    def _func(*args, **kwargs):
        try:
            module, klass = settings.DEFAULT_READER_ENGINE.rsplit('.', 1)
            reader_module = importlib.import_module(module)
            reader_class = getattr(reader_module, klass)

            if not hasattr(reader_class, 'apply_sql'):
                return HttpResponseBadRequest(content='SQL not supported')
        except (ModuleNotFoundError, AttributeError):
            return HttpResponseBadRequest(content='SQL not supported')

        return func(*args, **kwargs)

    return _func
