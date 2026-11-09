"""Call OasisManager computations, through the oasislmf CLI when cancellation needs it.

With the in-process celery pools (threads, gevent, eventlet) a task runs in the
worker's own process, so work done in the task's thread/greenlet can't be
stopped when the task is cancelled. For those pools `run_oasis_manager` runs
the computation as `oasislmf model <command>` in its own session instead, and
on cancellation kills the whole process group - the CLI, its multiprocessing
workers and any bash/ktools pipelines.

Everywhere else (prefork, which already cancels tasks itself, and any call
that has no CLI command or whose return value is needed) the OasisManager
method is called directly, as before.

`OASIS_WORKER_CLI_EXECUTION`: `auto` (default, CLI only on threads/gevent/
eventlet workers), `true` (always use the CLI where possible) or `false`.
"""
import json
import logging
import os
import queue
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections import deque

from celery.concurrency import ALIASES
from celery.exceptions import Terminated
from celery.signals import worker_init
from oasislmf.utils.exceptions import OasisException, OasisExceptionNoKeys

from ..conf.iniconf import settings
from . import task_cancel

logger = logging.getLogger(__name__)
cli_logger = logging.getLogger('oasislmf.cli')

# OasisManager method -> `oasislmf model` sub-command (calls whose return value isn't used)
CLI_COMMANDS = {
    'generate_oasis_files': 'generate-oasis-files',
    'generate_oasis_losses': 'generate-losses',
    'post_file_gen': 'generate-post-file-gen',
    'pre_loss': 'generate-pre-loss',
    'generate_losses_partial': 'generate-losses-chunk',
    'generate_losses_output': 'generate-losses-output',
    'post_analysis': 'run-postanalysis',
}

# pools that run tasks inside the worker process, where revoke can't stop a task
IN_PROCESS_POOLS = ('celery.concurrency.thread', 'celery.concurrency.gevent', 'celery.concurrency.eventlet')

# raised by oasislmf (computation/generate/files.py) when the lookup returned no keys
NO_KEYS_MESSAGE = 'No successful lookup results found in the keys file'

_OUTPUT_TAIL = 50


class OasisCLIError(OasisException):
    """An `oasislmf model` command exited with an error."""


_pool_in_process = False


@worker_init.connect
def _record_worker_pool(sender=None, **kwargs):
    global _pool_in_process
    _pool_in_process = _is_in_process_pool(getattr(sender, 'pool_cls', None))


def _is_in_process_pool(pool_cls):
    if isinstance(pool_cls, str):
        module = ALIASES.get(pool_cls, pool_cls).replace(':', '.').rsplit('.', 1)[0]
    else:
        module = getattr(pool_cls, '__module__', '')
    return module in IN_PROCESS_POOLS


_INI_CLI_EXECUTION = settings.get('worker', 'CLI_EXECUTION', fallback=None)


def cli_enabled():
    mode = os.environ.get('OASIS_WORKER_CLI_EXECUTION', _INI_CLI_EXECUTION) or 'auto'
    mode = str(mode).strip().lower()
    if mode in ('1', 'true', 'yes', 'on'):
        return True
    if mode in ('0', 'false', 'no', 'off'):
        return False
    return _pool_in_process


def run_oasis_manager(method, **kwargs):
    """`OasisManager().<method>(**kwargs)`, through the CLI when `cli_enabled()` and possible."""
    command = CLI_COMMANDS.get(method)
    if command and cli_enabled():
        return run_cli(command, kwargs)
    from oasislmf.manager import OasisManager
    return getattr(OasisManager(), method)(**kwargs)


def _cli_argv(command, config_fp):
    level = logging.getLevelName(logging.getLogger('oasislmf').getEffectiveLevel())
    if level not in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
        level = 'INFO'
    return [
        sys.executable, '-c', 'from oasislmf.cli.root import main; main()',
        'model', command, '--config', config_fp, '--log-level', level,
    ]


def run_cli(command, params):
    """Run `oasislmf model <command>` with `params` as its config, stopping it if the task is cancelled."""
    from celery import current_task
    task_id = getattr(getattr(current_task, 'request', None), 'id', None)

    with tempfile.TemporaryDirectory(prefix='oasis-cli-') as tmp:
        config_fp = os.path.join(tmp, 'oasislmf.json')
        with open(config_fp, 'w') as f:
            json.dump(params, f, default=str)

        proc = subprocess.Popen(
            _cli_argv(command, config_fp),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        logger.info('Running oasislmf model %s (pid %s)', command, proc.pid)

        lines, tail = queue.Queue(), deque(maxlen=_OUTPUT_TAIL)
        reader = threading.Thread(target=_read_lines, args=(proc.stdout, lines), daemon=True)
        reader.start()
        cancelled = False
        try:
            cancelled = _wait(proc, task_id, lines, tail)
        finally:
            # also runs on GreenletExit (gevent revoke) or worker shutdown
            stop_process_group(proc)
            reader.join(5)
            _emit(lines, tail)

    if cancelled or (task_id and task_cancel.is_cancelled(task_id)):
        # re-checked: the task_cancel watcher may have killed the process first
        raise Terminated(f'Task {task_id} cancelled')
    if proc.returncode != 0:
        output = '\n'.join(tail)
        if NO_KEYS_MESSAGE in output:
            raise OasisExceptionNoKeys(output)
        raise OasisCLIError(f'oasislmf model {command} failed with exit code {proc.returncode}:\n{output}')


def _wait(proc, task_id, lines, tail):
    interval = task_cancel.setting_seconds('TASK_CANCEL_POLL_INTERVAL', task_cancel.POLL_INTERVAL)
    while True:
        try:
            proc.wait(timeout=interval)
            return False
        except subprocess.TimeoutExpired:
            pass
        _emit(lines, tail)
        if task_id and task_cancel.is_cancelled(task_id):
            logger.info('Task %s cancelled: stopping oasislmf (process group %s)', task_id, proc.pid)
            return True


def _read_lines(stream, lines):
    with stream:
        for raw in iter(stream.readline, b''):
            line = raw.decode(errors='replace').rstrip()
            if line:
                lines.put(line)


def _emit(lines, tail):
    """Log CLI output from the calling (task) thread - task log handlers filter by thread."""
    while True:
        try:
            line = lines.get_nowait()
        except queue.Empty:
            return
        tail.append(line)
        cli_logger.info(line)


def _group_alive(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return False


def stop_process_group(proc, timeout=None):
    """SIGTERM every process left in `proc`'s group, SIGKILL whatever remains after `timeout`.

    Only signals a group that still has members, and waits for the whole group
    (not just the leader) before escalating.
    """
    timeout = task_cancel.setting_seconds('TASK_CANCEL_KILL_TIMEOUT', task_cancel.KILL_TIMEOUT) if timeout is None else timeout
    pgid = proc.pid
    proc.poll()  # reap the leader if it has exited, so it doesn't count as alive
    if not _group_alive(pgid):
        return
    os.killpg(pgid, signal.SIGTERM)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        proc.poll()
        if not _group_alive(pgid):
            break
        time.sleep(0.1)
    else:
        logger.warning('oasislmf process group %s ignored SIGTERM, sending SIGKILL', pgid)
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    proc.wait()
