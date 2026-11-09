"""Run heavy worker calls in a separate, killable process.

Work done inside a celery task's own thread (or greenlet) can't be stopped
when the task is cancelled: python has no safe way to kill a thread, and only
the prefork pool can signal the process running a task. `run_isolated` runs a
call in a fresh python process started in its own session, so on cancellation
the whole process group - the call itself, its multiprocessing workers and any
bash/ktools pipelines - is killed, whatever the celery pool type.

The child is a normal (non-daemonic) process, so the call can start its own
processes even when the worker uses prefork.

Cancellation is detected while waiting for the child:
  * threads / gevent / eventlet pools: the task id appears in
    `celery.worker.state.revoked` (see `task_cancel`).
  * prefork: celery SIGTERMs the pool process, raising SystemExit in the wait.
  * gevent: `revoke(terminate=True)` raises GreenletExit in the wait.

Log records from the child are sent back over its stdout pipe and re-emitted
in the task's thread so they reach the task log handlers; anything else the
child writes (to stdout or stderr) arrives on its stderr pipe and is logged
too. Both are `Popen` pipes, so reads are cooperative under gevent/eventlet.

Set `OASIS_WORKER_ISOLATED_EXECUTION=False` to run calls in-process instead.
"""
import importlib
import logging
import logging.handlers
import os
import pickle
import queue
import signal
import struct
import subprocess
import sys
import tempfile
import threading
import traceback

from celery.exceptions import Terminated

from ..conf.iniconf import settings
from . import task_cancel

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
OUTPUT_LOGGER = 'oasis.isolated.output'
_LEN = struct.Struct('>L')


class IsolatedProcessError(Exception):
    """The isolated process failed without returning a (picklable) result."""


# conf.ini values are read once; OASIS_WORKER_<OPTION> env vars are checked on every call
_INI = {
    option: settings.get('worker', option, fallback=None)
    for option in ('ISOLATED_EXECUTION', 'TASK_CANCEL_POLL_INTERVAL', 'TASK_CANCEL_KILL_TIMEOUT')
}


def _worker_setting(option, default):
    value = os.environ.get(f'OASIS_WORKER_{option}', _INI.get(option))
    return default if value in (None, '') else value


def isolation_enabled():
    return str(_worker_setting('ISOLATED_EXECUTION', True)).strip().lower() in ('1', 'true', 'yes', 'on')


def _poll_interval():
    return float(_worker_setting('TASK_CANCEL_POLL_INTERVAL', 1))


def _kill_timeout():
    return float(_worker_setting('TASK_CANCEL_KILL_TIMEOUT', 10))


def _resolve(target):
    module_name, _, attr = target.partition(':')
    obj = importlib.import_module(module_name)
    for part in attr.split('.'):
        obj = getattr(obj, part)
    return obj


def oasis_manager_call(method, **kwargs):
    from oasislmf.manager import OasisManager
    return getattr(OasisManager(), method)(**kwargs)


def run_oasis_manager(method, **kwargs):
    """`OasisManager().<method>(**kwargs)` in an isolated process."""
    return run_isolated(f'{__name__}:oasis_manager_call', method, **kwargs)


def run_isolated(target, *args, **kwargs):
    """Call `target` ('module:attr') with args/kwargs in a separate process group.

    Returns the call's result or re-raises its exception. Raises `Terminated`
    if the current task is cancelled while the call is running.
    """
    if not isolation_enabled():
        return _resolve(target)(*args, **kwargs)
    return _IsolatedCall(target, args, kwargs).run()


# --------------------------------------------------------------------------- parent

def _current_task_id():
    from celery import current_task
    return getattr(getattr(current_task, 'request', None), 'id', None)


def _logger_levels():
    levels = {'': logging.getLogger().getEffectiveLevel()}
    for name, lg in logging.root.manager.loggerDict.items():
        if isinstance(lg, logging.Logger) and lg.level:
            levels[name] = lg.level
    return levels


def _read_exact(f, n):
    data = b''
    while len(data) < n:
        chunk = f.read(n - len(data))
        if not chunk:
            return None
        data += chunk
    return data


class _IsolatedCall:

    def __init__(self, target, args, kwargs):
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.task_id = _current_task_id()
        self.records = queue.Queue()
        self.proc = None

    def run(self):
        with tempfile.TemporaryDirectory(prefix='oasis-isolated-') as tmp:
            payload_fp = os.path.join(tmp, 'payload.pkl')
            result_fp = os.path.join(tmp, 'result.pkl')
            with open(payload_fp, 'wb') as f:
                pickle.dump({
                    'target': self.target, 'args': self.args, 'kwargs': self.kwargs,
                    'log_levels': _logger_levels(),
                }, f)

            env = dict(os.environ)
            env['PYTHONPATH'] = os.pathsep.join(p for p in [PROJECT_ROOT, env.get('PYTHONPATH')] if p)
            self.proc = subprocess.Popen(
                [sys.executable, '-m', __name__, payload_fp, result_fp, str(os.getpid())],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                start_new_session=True, env=env,
            )
            logger.info('Running %s in isolated process %s', self.target, self.proc.pid)

            readers = [
                threading.Thread(target=self._read_records, args=(self.proc.stdout,), daemon=True),
                threading.Thread(target=self._read_output, args=(self.proc.stderr,), daemon=True),
            ]
            for t in readers:
                t.start()

            cancelled = False
            try:
                cancelled = self._wait()
            finally:
                # also runs on SystemExit (prefork SIGTERM) / GreenletExit (gevent kill)
                self._kill_group()
                for t in readers:
                    t.join(5)
                self._emit_records()

            if cancelled:
                raise Terminated(f'Task {self.task_id} cancelled')
            return self._result(result_fp)

    def _wait(self):
        interval = _poll_interval()
        while True:
            try:
                self.proc.wait(timeout=interval)
                return False
            except subprocess.TimeoutExpired:
                pass
            self._emit_records()
            if self.task_id and task_cancel.is_cancelled(self.task_id):
                logger.info('Task %s cancelled: killing isolated process group %s', self.task_id, self.proc.pid)
                return True

    def _kill_group(self):
        pgid = self.proc.pid
        if self.proc.poll() is None:
            try:
                os.killpg(pgid, signal.SIGTERM)
                self.proc.wait(timeout=_kill_timeout())
            except ProcessLookupError:
                pass
            except subprocess.TimeoutExpired:
                logger.warning('Isolated process group %s ignored SIGTERM, sending SIGKILL', pgid)
        # anything left in the group (stragglers, or everything after a timeout)
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.proc.wait()

    def _read_records(self, f):
        with f:
            while True:
                header = _read_exact(f, _LEN.size)
                if header is None:
                    return
                data = _read_exact(f, _LEN.unpack(header)[0])
                if data is None:
                    return
                self.records.put(logging.makeLogRecord(pickle.loads(data)))

    def _read_output(self, f):
        with f:
            for line in iter(f.readline, b''):
                line = line.decode(errors='replace').rstrip()
                if line:
                    # same level celery gives a task's redirected stdout (worker_redirect_stdouts_level)
                    self.records.put(logging.makeLogRecord({
                        'name': OUTPUT_LOGGER, 'levelno': logging.WARNING, 'levelname': 'WARNING', 'msg': line,
                    }))

    def _emit_records(self):
        """Re-emit child log records from this (the task's) thread."""
        ident, name = threading.get_ident(), threading.current_thread().name
        while True:
            try:
                record = self.records.get_nowait()
            except queue.Empty:
                return
            record.thread, record.threadName = ident, name  # task log handlers filter by thread
            lg = logging.getLogger(record.name)
            if record.levelno >= lg.getEffectiveLevel():
                lg.handle(record)

    def _result(self, result_fp):
        rc = self.proc.returncode
        try:
            with open(result_fp, 'rb') as f:
                status, value, tb = pickle.load(f)
        except FileNotFoundError:
            raise IsolatedProcessError(f'Isolated process for {self.target} exited with code {rc} without a result')
        except Exception as e:
            raise IsolatedProcessError(f'Could not load result of {self.target}: {e!r}')
        if status == 'ok':
            return value
        if isinstance(value, BaseException):
            if value.__traceback__ is None:
                # tracebacks are only pickled when tblib's support is installed (oasislmf does)
                value.add_note(f'--- traceback in isolated process ---\n{tb}')
            raise value
        raise IsolatedProcessError(f'{self.target} failed in isolated process:\n{tb}')


# --------------------------------------------------------------------------- child

class _PipeLogHandler(logging.Handler):
    """Sends pickled log records (as `SocketHandler` does) to the parent over a pipe."""

    def __init__(self, fd):
        super().__init__()
        self.fd = fd

    def emit(self, record):
        try:
            data = logging.handlers.SocketHandler.makePickle(self, record)
            with self.lock:
                view = memoryview(data)
                while view:
                    view = view[os.write(self.fd, view):]
        except Exception:
            self.handleError(record)


def _set_parent_death_signal(parent_pid):
    """Get SIGTERM if the worker dies (e.g. OOM killed), so the group isn't orphaned."""
    try:
        import ctypes
        libc = ctypes.CDLL(None, use_errno=True)
        libc.prctl(1, signal.SIGTERM)  # PR_SET_PDEATHSIG
    except Exception:
        pass
    if os.getppid() != parent_pid:
        os.kill(os.getpid(), signal.SIGTERM)


def _install_group_term_handler():
    """On SIGTERM take the whole process group down (forked children keep default handling)."""
    leader = os.getpid()

    def handler(signum, frame):
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        if os.getpid() == leader:
            os.killpg(os.getpgrp(), signal.SIGTERM)
        else:
            os.kill(os.getpid(), signal.SIGTERM)

    signal.signal(signal.SIGTERM, handler)


def _child_main(payload_fp, result_fp, parent_pid):
    _install_group_term_handler()
    _set_parent_death_signal(parent_pid)

    # stdout carries pickled log records: keep it for that, send any other output
    # (prints, subprocesses inheriting fd 1) to stderr
    sys.stdout.flush()
    log_fd = os.dup(1)
    os.dup2(2, 1)

    with open(payload_fp, 'rb') as f:
        payload = pickle.load(f)

    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(_PipeLogHandler(log_fd))
    for name, level in payload['log_levels'].items():
        logging.getLogger(name or None).setLevel(level)

    try:
        result = ('ok', _resolve(payload['target'])(*payload['args'], **payload['kwargs']), None)
    except BaseException as e:
        result = ('error', e, traceback.format_exc())

    try:
        data = pickle.dumps(result)
    except Exception:
        data = pickle.dumps(('error', None, result[2] or f'unpicklable result: {result[1]!r}'))
    with open(result_fp, 'wb') as f:
        f.write(data)
    logging.shutdown()


if __name__ == '__main__':
    _child_main(sys.argv[1], sys.argv[2], int(sys.argv[3]))
