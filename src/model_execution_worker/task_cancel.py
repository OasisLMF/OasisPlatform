"""Cancellation support for tasks run by in-process celery pools (threads, gevent).

`revoke(terminate=True)` only works for the prefork pool, where celery sends a
signal to the pool *process* running the task. With `--pool threads` the
thread pool raises `NotImplementedError` (it can't signal a thread), so the
task keeps running, and with any pool the processes a task spawns
(the oasislmf bash/ktools run, lookup multiprocessing workers) are never
signalled and are left orphaned.

This module tracks which OS thread is running each task and, when a task is
cancelled, kills the process trees started from that thread:

* The task id is added to `celery.worker.state.revoked` *before* celery tries
  to terminate the task, so for in-process pools a watcher thread can detect
  the cancellation even though `terminate_job` then fails.
* Linux lists the children created by each thread in
  `/proc/<pid>/task/<tid>/children`, which identifies a task's processes
  without patching subprocess/os.fork.

Prefork tasks are still stopped by celery's SIGTERM; `OasisWorkerTask` calls
`kill_task_processes` while the task unwinds so its children are not orphaned.

Note: with the gevent pool every task runs on the same OS thread, so the
children of different tasks can't be told apart. Process cleanup there is only
done when a single task is running (`--concurrency 1`).
"""
import logging
import os
import threading
import time

import psutil
from celery import current_task
from celery.exceptions import Terminated
from celery.signals import worker_ready
from celery.worker import state as worker_state

from ..conf.iniconf import settings

logger = logging.getLogger(__name__)

# seconds; override with OASIS_WORKER_TASK_CANCEL_POLL_INTERVAL / OASIS_WORKER_TASK_CANCEL_KILL_TIMEOUT
POLL_INTERVAL = settings.getint('worker', 'TASK_CANCEL_POLL_INTERVAL', fallback=2)
KILL_TIMEOUT = settings.getint('worker', 'TASK_CANCEL_KILL_TIMEOUT', fallback=10)


class _RunningTask:
    __slots__ = ('task_id', 'pid', 'tid', 'started', 'cancelled')

    def __init__(self, task_id):
        self.task_id = task_id
        self.pid = os.getpid()
        self.tid = threading.get_native_id()
        self.started = time.time()
        self.cancelled = False


_running = {}
_lock = threading.Lock()


def register(task_id):
    """Record the thread running `task_id`. Call from the thread executing the task."""
    if task_id:
        with _lock:
            _running[task_id] = _RunningTask(task_id)


def unregister(task_id):
    with _lock:
        _running.pop(task_id, None)


def is_cancelled(task_id=None):
    """True if `task_id` (default: the current task) has been revoked on this worker."""
    if task_id is None:
        task_id = getattr(getattr(current_task, 'request', None), 'id', None)
    if not task_id:
        return False
    entry = _running.get(task_id)
    return bool(entry and entry.cancelled) or task_id in worker_state.revoked


def raise_if_cancelled(task_id=None):
    if is_cancelled(task_id):
        raise Terminated(f'Task {task_id or current_task.request.id} cancelled')


def _thread_children(pid, tid):
    """Direct child pids created by thread `tid` of process `pid` (None if unsupported)."""
    try:
        with open(f'/proc/{pid}/task/{tid}/children') as f:
            return [int(p) for p in f.read().split()]
    except (FileNotFoundError, ProcessLookupError):
        return None


def task_processes(task_id):
    """Root processes started by the task (their descendants are found when killing)."""
    with _lock:
        entry = _running.get(task_id)
        if entry is None:
            return []
        siblings = [e for e in _running.values() if e is not entry and e.pid == entry.pid]

    if any(e.tid == entry.tid for e in siblings):
        # gevent with --concurrency > 1: tasks share a thread, can't attribute children
        logger.warning('Task %s shares a thread with other running tasks, '
                       'not killing its child processes', task_id)
        return []

    pids = _thread_children(entry.pid, entry.tid)
    if pids is None:
        # /proc/<pid>/task/<tid>/children unavailable (CONFIG_PROC_CHILDREN not set)
        if siblings:
            logger.warning('Cannot attribute child processes of task %s: '
                           '/proc thread children unavailable', task_id)
            return []
        try:
            return [p for p in psutil.Process(entry.pid).children()
                    if p.create_time() >= entry.started - 1]
        except psutil.NoSuchProcess:
            return []

    procs = []
    for pid in pids:
        try:
            procs.append(psutil.Process(pid))
        except psutil.NoSuchProcess:
            pass
    return procs


def kill_process_tree(roots, timeout=KILL_TIMEOUT):
    """SIGTERM `roots` and all their descendants, SIGKILL anything left after `timeout`."""
    procs = []
    for root in roots:
        try:
            # collect descendants before signalling, so reparented orphans are still caught
            procs.extend(root.children(recursive=True))
        except psutil.NoSuchProcess:
            pass
        procs.append(root)
    for p in procs:
        try:
            p.terminate()
        except psutil.NoSuchProcess:
            pass
    # Forked python children inherit the celery worker's SIGTERM handler and may ignore it
    for p in _wait_gone(procs, timeout):
        try:
            p.kill()
        except psutil.NoSuchProcess:
            pass
    return len(procs)


def _is_gone(proc):
    try:
        return proc.status() == psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return True


def _wait_gone(procs, timeout):
    """Wait for `procs` to exit, return those still alive.

    Plain polling instead of `psutil.wait_procs`, which uses `select.poll`
    (removed by eventlet's monkey patching).
    """
    deadline = time.monotonic() + timeout
    alive = [p for p in procs if not _is_gone(p)]
    while alive and time.monotonic() < deadline:
        time.sleep(0.1)
        alive = [p for p in alive if not _is_gone(p)]
    return alive


def kill_task_processes(task_id):
    """Kill every process tree started by the thread running `task_id`."""
    if not task_id:
        return 0
    roots = task_processes(task_id)
    if not roots:
        return 0
    logger.info('Task %s cancelled: killing child processes %s', task_id, [p.pid for p in roots])
    return kill_process_tree(roots)


def cleanup_task_processes(task_id):
    """`kill_task_processes` that never raises, for use while a task is unwinding."""
    try:
        return kill_task_processes(task_id)
    except Exception:
        logger.exception('Failed to kill child processes of task %s', task_id)
        return 0


def check_revoked():
    """Kill the processes of any running task that has been revoked. Returns cancelled ids."""
    with _lock:
        newly_cancelled = [e for e in _running.values()
                           if not e.cancelled and e.task_id in worker_state.revoked]
        for entry in newly_cancelled:
            entry.cancelled = True
    for entry in newly_cancelled:
        try:
            kill_task_processes(entry.task_id)
        except Exception:
            logger.exception('Failed to kill processes of cancelled task %s', entry.task_id)
    return [e.task_id for e in newly_cancelled]


def _watch(interval):
    while True:
        try:
            check_revoked()
        except Exception:
            logger.exception('Task cancel watcher error')
        time.sleep(interval)


_watcher = None


def start_watcher(interval=POLL_INTERVAL):
    """Start the revoke watcher in this (worker main) process, once."""
    global _watcher
    if _watcher is None or not _watcher.is_alive():
        _watcher = threading.Thread(target=_watch, args=(interval,), name='oasis-task-cancel', daemon=True)
        _watcher.start()
    return _watcher


@worker_ready.connect
def _start_watcher_on_worker_ready(**kwargs):
    # Runs in the worker's main process: this covers the threads/gevent/eventlet pools,
    # whose tasks run in that process. Prefork children don't inherit the thread.
    start_watcher()
