import importlib
import os
from unittest import mock

import pytest

from src.conf import celeryconf_v1, celeryconf_v2

RETRY_ENV = ('OASIS_WORKER_TASK_MAX_RETRIES', 'OASIS_WORKER_TASK_RETRY_DELAY')


@pytest.fixture
def reload_conf():
    """Reload a celery conf module under a patched environment, then restore it."""
    loaded = []

    def _reload(module, env):
        clean = {k: v for k, v in os.environ.items() if k not in RETRY_ENV}
        with mock.patch.dict(os.environ, {**clean, **env}, clear=True):
            loaded.append(module)
            return importlib.reload(module)

    yield _reload
    for module in loaded:
        importlib.reload(module)


@pytest.mark.parametrize('module', [celeryconf_v1, celeryconf_v2])
def test_task_retries___not_set___defaults(reload_conf, module):
    conf = reload_conf(module, {})
    assert conf.worker_task_kwargs['max_retries'] == 2
    assert conf.worker_task_kwargs['default_retry_delay'] == 6
    assert conf.worker_task_kwargs['autoretry_for'] == (Exception,)


@pytest.mark.parametrize('module', [celeryconf_v1, celeryconf_v2])
@pytest.mark.parametrize('retries, delay', [(0, 0), (5, 30)])
def test_task_retries___set_in_env___env_values_used(reload_conf, module, retries, delay):
    conf = reload_conf(module, {
        'OASIS_WORKER_TASK_MAX_RETRIES': str(retries),
        'OASIS_WORKER_TASK_RETRY_DELAY': str(delay),
    })
    assert conf.worker_task_kwargs['max_retries'] == retries
    assert conf.worker_task_kwargs['default_retry_delay'] == delay
