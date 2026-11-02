"""
Checks that AWS_LOCATION env vars reach the storage objects the server and the
worker actually build. Both are created at import time (Django settings /
module-level `filestore`), so each case runs in a fresh interpreter.

Section-specific vars (OASIS_SERVER_AWS_LOCATION, OASIS_WORKER_AWS_LOCATION)
let the server and worker write under different bucket prefixes.
"""
import json
import os
import subprocess
import sys
from unittest import TestCase

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))

SERVER_PROBE = """
import json
import django
django.setup()
from django.conf import settings
from django.core.files.storage import default_storage
print(json.dumps({
    'settings': settings.AWS_LOCATION,
    'default_storage': default_storage.location,
}))
"""

WORKER_PROBE = """
import json
from src.common.filestore.filestore import get_filestore
from src.conf.iniconf import settings
from src.model_execution_worker import distributed_tasks
print(json.dumps({
    'distributed_tasks': distributed_tasks.filestore.location,
    'get_filestore': get_filestore(settings).location,
}))
"""

LOCATION_VARS = ('OASIS_AWS_LOCATION', 'OASIS_SERVER_AWS_LOCATION', 'OASIS_WORKER_AWS_LOCATION')


def run_probe(probe, **env_overrides):
    env = {k: v for k, v in os.environ.items() if k not in LOCATION_VARS}
    env.update({
        'OASIS_STORAGE_TYPE': 'S3',
        'OASIS_AWS_BUCKET_NAME': 'example-bucket',
        'DJANGO_SETTINGS_MODULE': 'src.server.oasisapi.settings',
        **env_overrides,
    })
    result = subprocess.run(
        [sys.executable, '-c', probe],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        raise AssertionError(f'probe failed:\n{result.stderr}')
    return json.loads(result.stdout.strip().splitlines()[-1])


class StorageLocationFromEnv(TestCase):
    def test_section_specific_vars___server_and_worker_use_their_own_prefix(self):
        env = {'OASIS_SERVER_AWS_LOCATION': 'oasis/server', 'OASIS_WORKER_AWS_LOCATION': 'oasis/worker'}

        self.assertEqual(run_probe(SERVER_PROBE, **env), {
            'settings': 'oasis/server',
            'default_storage': 'oasis/server',
        })
        self.assertEqual(run_probe(WORKER_PROBE, **env), {
            'distributed_tasks': 'oasis/worker',
            'get_filestore': 'oasis/worker',
        })

    def test_global_var_only___server_and_worker_share_the_prefix(self):
        env = {'OASIS_AWS_LOCATION': 'oasis/files'}

        self.assertEqual(run_probe(SERVER_PROBE, **env)['default_storage'], 'oasis/files')
        self.assertEqual(run_probe(WORKER_PROBE, **env)['distributed_tasks'], 'oasis/files')

    def test_global_and_section_vars___section_var_wins(self):
        env = {
            'OASIS_AWS_LOCATION': 'oasis/files',
            'OASIS_SERVER_AWS_LOCATION': 'oasis/server',
            'OASIS_WORKER_AWS_LOCATION': 'oasis/worker',
        }

        self.assertEqual(run_probe(SERVER_PROBE, **env)['default_storage'], 'oasis/server')
        self.assertEqual(run_probe(WORKER_PROBE, **env)['distributed_tasks'], 'oasis/worker')
