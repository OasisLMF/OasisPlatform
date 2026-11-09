"""Functions run by test_isolated.py in an isolated process (must be importable by the child)."""
import json
import logging
import multiprocessing
import os
import subprocess
import sys
import time


def add(a, b=0):
    return {'sum': a + b, 'pid': os.getpid()}


def fail():
    raise ValueError('bad input')


def hard_exit():
    os._exit(3)


def log_and_print():
    logging.getLogger('oasislmf').info('info from child')
    logging.getLogger('oasislmf').debug('debug from child')
    print('printed by child', flush=True)
    os.system('echo from a subprocess >&2')
    return 'ok'


def busy_with_children(pid_file):
    """Like a model run: bash pipeline, forked workers and CPU-bound python, all at once."""
    bash = subprocess.Popen(['bash', '-c', 'sleep 300 & echo $!; wait'], stdout=subprocess.PIPE)
    grandchild = int(bash.stdout.readline())
    forked = multiprocessing.get_context('fork').Process(target=time.sleep, args=(300,))
    forked.start()
    with open(pid_file + '.tmp', 'w') as f:
        json.dump({'runner': os.getpid(), 'bash': bash.pid, 'grandchild': grandchild, 'forked': forked.pid}, f)
    os.rename(pid_file + '.tmp', pid_file)
    n = 0
    while True:  # CPU-bound, never yields
        n += 1


if __name__ == '__main__':
    sys.exit('not a script')
