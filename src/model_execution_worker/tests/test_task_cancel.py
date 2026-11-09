import multiprocessing
import subprocess
import threading
import time
from unittest import TestCase, mock

import psutil
from celery import Celery
from celery.exceptions import Terminated
from celery.worker import state as worker_state

from src.model_execution_worker import task_cancel
from src.model_execution_worker.celery_error_handler import OasisWorkerTask


def _alive(pid):
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def _wait_dead(pid, timeout=5):
    end = time.time() + timeout
    while time.time() < end:
        if not _alive(pid):
            return True
        time.sleep(0.05)
    return False


class FakeTaskThread(threading.Thread):
    """Mimics a celery pool thread running a task that spawns a bash run and a forked worker."""

    def __init__(self, task_id):
        super().__init__(daemon=True)
        self.task_id = task_id
        self.ready = threading.Event()
        self.release = threading.Event()
        self.bash = None
        self.grandchild_pid = None
        self.forked = None

    def run(self):
        task_cancel.register(self.task_id)
        try:
            # bash with a background child, like the oasislmf run script spawning ktools
            self.bash = subprocess.Popen(['bash', '-c', 'sleep 60 & echo $!; wait'], stdout=subprocess.PIPE)
            self.grandchild_pid = int(self.bash.stdout.readline())
            self.forked = multiprocessing.get_context('fork').Process(target=time.sleep, args=(60,))
            self.forked.start()
            self.ready.set()
            self.release.wait(30)
        finally:
            task_cancel.unregister(self.task_id)

    def pids(self):
        return [self.bash.pid, self.grandchild_pid, self.forked.pid]

    def cleanup(self):
        for pid in self.pids():
            try:
                psutil.Process(pid).kill()
            except psutil.NoSuchProcess:
                pass
        self.release.set()
        self.bash.wait(5)
        self.forked.join(5)
        self.join(5)


class TaskProcessKillTests(TestCase):

    def setUp(self):
        self.threads = []

    def tearDown(self):
        for t in self.threads:
            worker_state.revoked.discard(t.task_id)
            t.cleanup()

    def start_task(self, task_id):
        t = FakeTaskThread(task_id)
        self.threads.append(t)
        t.start()
        self.assertTrue(t.ready.wait(10))
        return t

    def test_task_processes___only_returns_children_of_the_tasks_thread(self):
        a = self.start_task('task-a')
        b = self.start_task('task-b')

        self.assertEqual({p.pid for p in task_cancel.task_processes('task-a')}, {a.bash.pid, a.forked.pid})
        self.assertEqual({p.pid for p in task_cancel.task_processes('task-b')}, {b.bash.pid, b.forked.pid})

    def test_kill_task_processes___kills_whole_tree_and_leaves_other_tasks_running(self):
        a = self.start_task('task-a')
        b = self.start_task('task-b')

        task_cancel.kill_task_processes('task-a')

        for pid in a.pids():
            self.assertTrue(_wait_dead(pid), f'pid {pid} of cancelled task still running')
        for pid in b.pids():
            self.assertTrue(_alive(pid), f'pid {pid} of other task was killed')

    def test_check_revoked___cancels_revoked_task_once(self):
        a = self.start_task('task-a')
        b = self.start_task('task-b')
        worker_state.revoked.add('task-a')

        self.assertEqual(task_cancel.check_revoked(), ['task-a'])
        self.assertEqual(task_cancel.check_revoked(), [])
        self.assertTrue(task_cancel.is_cancelled('task-a'))
        self.assertFalse(task_cancel.is_cancelled('task-b'))
        for pid in a.pids():
            self.assertTrue(_wait_dead(pid))
        for pid in b.pids():
            self.assertTrue(_alive(pid))

    def test_tasks_sharing_a_thread___children_are_not_attributed(self):
        # gevent with --concurrency > 1 runs every task on the same OS thread
        a = self.start_task('task-a')
        task_cancel._running['task-c'] = task_cancel._RunningTask('task-c')
        task_cancel._running['task-c'].tid = task_cancel._running['task-a'].tid
        try:
            self.assertEqual(task_cancel.task_processes('task-a'), [])
            task_cancel.kill_task_processes('task-a')
            for pid in a.pids():
                self.assertTrue(_alive(pid))
        finally:
            task_cancel.unregister('task-c')

    def test_kill_process_tree___sigkills_process_ignoring_sigterm(self):
        # e.g. a forked child that inherited the celery worker's SIGTERM handler
        proc = subprocess.Popen(['bash', '-c', 'trap "" TERM; sleep 60 & wait; sleep 60'])
        try:
            time.sleep(0.2)
            start = time.time()
            task_cancel.kill_process_tree([psutil.Process(proc.pid)], timeout=1)
            self.assertTrue(_wait_dead(proc.pid))
            self.assertLess(time.time() - start, 5)
        finally:
            proc.kill()
            proc.wait()

    def test_cleanup_task_processes___never_raises(self):
        with mock.patch.object(task_cancel, 'kill_task_processes', side_effect=AttributeError('poll')):
            self.assertEqual(task_cancel.cleanup_task_processes('task-a'), 0)

    def test_unknown_task___nothing_killed(self):
        self.assertEqual(task_cancel.kill_task_processes('not-running'), 0)
        self.assertEqual(task_cancel.kill_task_processes(None), 0)


app = Celery('test_task_cancel', task_cls=OasisWorkerTask)
app.conf.task_always_eager = False


@app.task(bind=True, name='cancel_test_ok')
def ok_task(self):
    return 'done'


@app.task(bind=True, name='cancel_test_fails')
def failing_task(self):
    raise RuntimeError('bash run killed')


class OasisWorkerTaskCancelTests(TestCase):

    def tearDown(self):
        worker_state.revoked.discard('tid-1')

    def test_not_cancelled___result_and_errors_unchanged(self):
        self.assertEqual(ok_task.apply(task_id='tid-1').get(), 'done')
        with self.assertRaises(RuntimeError):
            failing_task.apply(task_id='tid-1').get()

    def test_cancelled_task_that_fails___raises_terminated(self):
        worker_state.revoked.add('tid-1')
        res = failing_task.apply(task_id='tid-1')
        self.assertIsInstance(res.result, Terminated)

    def test_cancelled_task_that_completes___raises_terminated(self):
        worker_state.revoked.add('tid-1')
        res = ok_task.apply(task_id='tid-1')
        self.assertIsInstance(res.result, Terminated)

    def test_retry_of_cancelled_task___raises_terminated(self):
        worker_state.revoked.add('tid-1')
        failing_task.push_request(id='tid-1')
        try:
            with self.assertRaises(Terminated):
                failing_task.retry(exc=RuntimeError('x'))
        finally:
            failing_task.pop_request()

    def test_task_is_unregistered_after_run(self):
        ok_task.apply(task_id='tid-1')
        self.assertNotIn('tid-1', task_cancel._running)
