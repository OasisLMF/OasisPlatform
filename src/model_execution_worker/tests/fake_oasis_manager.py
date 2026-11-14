"""Stand-in for OasisManager, run in the child process by test_oasis_subprocess_runner.py."""
import json
import logging
import multiprocessing
import os
import pathlib
import subprocess
import time

logger = logging.getLogger('oasislmf.fake')


def add(a, b):
    return {'sum': a + b, 'pid': os.getpid()}


class FakeManager:

    def ok(self, **kwargs):
        logger.info('running ok')
        return {'kwargs': kwargs, 'path': pathlib.Path('/tmp/x')}

    def fail(self, **kwargs):
        raise ValueError('Something went wrong')

    def client_error(self, **kwargs):
        # defined locally, like an exception from client code: can't be pickled or imported by the worker
        class ClientLookupError(Exception):
            pass
        raise ClientLookupError('bad lookup data')

    def crash(self, **kwargs):
        print('about to crash', flush=True)
        os._exit(9)

    def leave_background(self, pid_file):
        subprocess.Popen(['bash', '-c', f'echo $$ > {pid_file}; exec sleep 300'])
        time.sleep(0.5)

    def busy(self, pid_file):
        # like a model run: bash pipeline with a background child, a forked worker, CPU-bound python
        bash = subprocess.Popen(['bash', '-c', 'sleep 300 & echo $!; wait'], stdout=subprocess.PIPE)
        grandchild = int(bash.stdout.readline())
        forked = multiprocessing.get_context('fork').Process(target=time.sleep, args=(300,))
        forked.start()
        with open(pid_file + '.tmp', 'w') as f:
            json.dump({'runner': os.getpid(), 'bash': bash.pid, 'bash_child': grandchild, 'forked': forked.pid}, f)
        os.rename(pid_file + '.tmp', pid_file)
        while True:
            pass
