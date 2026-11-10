"""Run OasisManager methods and other worker functions in a separate, killable process.

With the in-process celery pools (threads, gevent, eventlet) a task runs in the
worker's own process, so work done in the task's thread/greenlet can't be
stopped when the task is cancelled. For those pools `utils.run_oasis` (OasisManager
methods) and `utils.run_function` (e.g. the keys lookup helpers in utils) run the
call in a fresh Python process in its own session instead, and on cancellation
kill the whole process group - the child, its multiprocessing workers and any
bash/ktools pipelines.

The child is this module run with `-m` (see `child_main`). It makes the same call
as the in-process path. Request and result are JSON files; exceptions come back
as text (type names, message, traceback), so client exceptions that can't be
pickled or imported in the worker keep their traceback.

Elsewhere (prefork, which already cancels tasks itself) the call is made
directly, as before.

`OASIS_WORKER_SUBPROCESS_EXECUTION` (or `SUBPROCESS_EXECUTION` in conf.ini):
`auto` (default, subprocess only on threads/gevent/eventlet workers), `true`
(always) or `false` (never).
"""
import importlib
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
import traceback
from collections import deque

from celery.concurrency import ALIASES
from celery.exceptions import Terminated
from celery.signals import worker_init
from celery.worker import state as worker_state
from oasislmf.utils.exceptions import OasisException, OasisExceptionNoKeys

from ..conf.iniconf import settings

logger = logging.getLogger(__name__)
# re-emits the child's output (the task log handler is on the root logger, so it's captured there)
output_logger = logging.getLogger(f'{__name__}.output')

MANAGER = 'oasislmf.manager:OasisManager'

# pools that run tasks inside the worker process, where revoke can't stop a task
IN_PROCESS_POOLS = ('celery.concurrency.thread', 'celery.concurrency.gevent', 'celery.concurrency.eventlet')

_NO_KEYS_TYPE = f'{OasisExceptionNoKeys.__module__}.{OasisExceptionNoKeys.__qualname__}'
_OUTPUT_TAIL = 50


def setting_seconds(option, default):
    """A [worker] setting in seconds (OASIS_WORKER_<OPTION> env var or conf.ini), float allowed."""
    value = os.environ.get(f'OASIS_WORKER_{option}') or settings.get('worker', option, fallback=None)
    try:
        return float(value) if value not in (None, '') else default
    except ValueError:
        logger.warning('Invalid value %r for %s, using %s', value, option, default)
        return default


# how often a running child checks for a revoke, and how long it gets after SIGTERM before SIGKILL
POLL_INTERVAL = setting_seconds('TASK_CANCEL_POLL_INTERVAL', 2)
KILL_TIMEOUT = setting_seconds('TASK_CANCEL_KILL_TIMEOUT', 10)


class OasisRunnerError(OasisException):
    """A function or OasisManager method run in a subprocess failed."""


def _current_task_id():
    from celery import current_task
    return getattr(getattr(current_task, 'request', None), 'id', None)


def is_cancelled(task_id=None):
    """True if `task_id` (default: the current task) has been revoked on this worker.

    Celery adds the id to `worker_state.revoked` before it tries to terminate the
    task, so this works for the in-process pools even though terminating fails there.
    """
    task_id = task_id or _current_task_id()
    return bool(task_id) and task_id in worker_state.revoked


def raise_if_cancelled(task_id=None):
    task_id = task_id or _current_task_id()
    if is_cancelled(task_id):
        raise Terminated(f'Task {task_id} cancelled')


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


_INI_SUBPROCESS_EXECUTION = settings.get('worker', 'SUBPROCESS_EXECUTION', fallback=None)


def subprocess_enabled():
    mode = os.environ.get('OASIS_WORKER_SUBPROCESS_EXECUTION', _INI_SUBPROCESS_EXECUTION) or 'auto'
    mode = str(mode).strip().lower()
    if mode in ('1', 'true', 'yes', 'on'):
        return True
    if mode in ('0', 'false', 'no', 'off'):
        return False
    return _pool_in_process


# this module's import name and the directory its top-level package is in, for `python -m`
_MODULE = __spec__.name if __spec__ else __name__
_IMPORT_ROOT = os.path.abspath(__file__)
for _ in _MODULE.split('.'):
    _IMPORT_ROOT = os.path.dirname(_IMPORT_ROOT)


def _child_argv(request_fp, result_fp):
    return [sys.executable, '-u', '-m', _MODULE, request_fp, result_fp]


def _child_env():
    # the child must be able to import this package whatever the working directory is
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join(filter(None, [_IMPORT_ROOT, env.get('PYTHONPATH')]))
    return env


def _log_level():
    level = logging.getLevelName(logging.getLogger('oasislmf').getEffectiveLevel())
    return level if level in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL') else 'INFO'


def run_in_subprocess(target, kwargs, method=None):
    """Run `target(**kwargs)` in a child process, stopping it if the task is cancelled.

    `target` is a `'package.module:name'` import path to a function, or to a class
    when `method` is given (`target().<method>(**kwargs)`, e.g. an OasisManager method).
    `kwargs` must be JSON serialisable (paths and other non-JSON values are sent as
    strings). Returns the return value, converted the same way.
    """
    task_id = _current_task_id()
    label = f"{target.rsplit(':', 1)[-1].rsplit('.', 1)[-1]}.{method}" if method else target

    with tempfile.TemporaryDirectory(prefix='oasis-subprocess-') as tmp:
        request_fp = os.path.join(tmp, 'request.json')
        result_fp = os.path.join(tmp, 'result.json')
        with open(request_fp, 'w') as f:
            json.dump({'target': target, 'method': method, 'kwargs': kwargs, 'log_level': _log_level()},
                      f, default=str)

        proc = subprocess.Popen(
            _child_argv(request_fp, result_fp),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            env=_child_env(), start_new_session=True,
        )
        logger.info('Running %s in subprocess (pid %s)', label, proc.pid)

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

        if cancelled:
            raise Terminated(f'Task {task_id} cancelled')
        result = _read_result(result_fp)

    if result is None:
        raise OasisRunnerError(
            f'{label} exited with code {proc.returncode} without a result:\n' + '\n'.join(tail))
    if result['ok']:
        return result['value']
    if _NO_KEYS_TYPE in result['types']:
        raise OasisExceptionNoKeys(result['message'])
    raise OasisRunnerError(
        f"{label} failed with {result['types'][0]}: {result['message']}\n\n"
        f"Traceback from the subprocess:\n{result['traceback']}")


def _read_result(result_fp):
    try:
        with open(result_fp) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _wait(proc, task_id, lines, tail):
    interval = setting_seconds('TASK_CANCEL_POLL_INTERVAL', POLL_INTERVAL)
    while True:
        try:
            proc.wait(timeout=interval)
            return False
        except subprocess.TimeoutExpired:
            pass
        _emit(lines, tail)
        if is_cancelled(task_id):
            logger.info('Task %s cancelled: stopping oasislmf (process group %s)', task_id, proc.pid)
            return True


def _read_lines(stream, lines):
    with stream:
        for raw in iter(stream.readline, b''):
            line = raw.decode(errors='replace').rstrip()
            if line:
                lines.put(line)


def _emit(lines, tail):
    """Log the child's output from the calling (task) thread - task log handlers filter by thread."""
    while True:
        try:
            line = lines.get_nowait()
        except queue.Empty:
            return
        tail.append(line)
        output_logger.info(line)


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
    timeout = setting_seconds('TASK_CANCEL_KILL_TIMEOUT', KILL_TIMEOUT) if timeout is None else timeout
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


# --- child side: `python -m <this module> <request.json> <result.json>` ---

def load_object(path):
    """`'package.module:Name.attr'` -> the object."""
    module_name, _, attr = path.partition(':')
    obj = importlib.import_module(module_name)
    for part in filter(None, attr.split('.')):
        obj = getattr(obj, part)
    return obj


def _class_name(cls):
    return f'{cls.__module__}.{cls.__qualname__}'


def _run_request(request):
    try:
        func = load_object(request['target'])
        if request.get('method'):
            func = getattr(func(), request['method'])
        value = func(**request['kwargs'])
        return {'ok': True, 'value': value}
    except Exception as exc:
        return {
            'ok': False,
            'types': [_class_name(c) for c in type(exc).__mro__ if c not in (object, BaseException)],
            'message': str(exc),
            'traceback': traceback.format_exc(),
        }


def child_main(request_fp, result_fp):
    """Run the requested function or method and write its result (see `run_in_subprocess`)."""
    with open(request_fp) as f:
        request = json.load(f)
    logging.basicConfig(level=request.get('log_level', 'INFO'), stream=sys.stdout,
                        format='%(message)s', force=True)

    result = _run_request(request)

    # values that aren't JSON (e.g. paths, client pre-analysis objects) are sent as strings
    tmp_fp = result_fp + '.tmp'
    with open(tmp_fp, 'w') as f:
        json.dump(result, f, default=str)
    os.replace(tmp_fp, result_fp)
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(child_main(sys.argv[1], sys.argv[2]))
