import json
import logging
import os
import tempfile
import threading
import time
from unittest import TestCase, mock

import psutil
from celery.exceptions import Terminated
from celery.worker import state as worker_state

from src.model_execution_worker import isolated

TARGETS = 'src.model_execution_worker.tests.isolated_targets'


def _alive(pid):
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


@mock.patch.dict(os.environ, {'OASIS_WORKER_ISOLATED_EXECUTION': 'True', 'OASIS_WORKER_TASK_CANCEL_KILL_TIMEOUT': '2'})
class RunIsolatedTests(TestCase):

    def test_result_is_returned_from_a_separate_process(self):
        res = isolated.run_isolated(f'{TARGETS}:add', 2, b=3)
        self.assertEqual(res['sum'], 5)
        self.assertNotEqual(res['pid'], os.getpid())

    def test_disabled___runs_in_process(self):
        with mock.patch.dict(os.environ, {'OASIS_WORKER_ISOLATED_EXECUTION': 'False'}):
            self.assertEqual(isolated.run_isolated(f'{TARGETS}:add', 1)['pid'], os.getpid())

    def test_exception_type_is_preserved(self):
        with self.assertRaises(ValueError) as ctx:
            isolated.run_isolated(f'{TARGETS}:fail')
        self.assertIn('bad input', str(ctx.exception))
        self.assertTrue(any('isolated process' in n for n in ctx.exception.__notes__))

    def test_process_exiting_without_result___raises(self):
        with self.assertRaises(isolated.IsolatedProcessError):
            isolated.run_isolated(f'{TARGETS}:hard_exit')

    def test_exception_that_cannot_be_unpickled___details_are_kept(self):
        with self.assertRaises(isolated.IsolatedProcessError) as ctx:
            isolated.run_isolated(f'{TARGETS}:raise_client_error')
        msg = str(ctx.exception)
        self.assertIn('ClientLookupError: location 42: peril code not supported', msg)
        self.assertIn('could not be unpickled', msg)
        self.assertIn('in raise_client_error', msg)  # child traceback

    def test_exception_that_cannot_be_pickled___details_are_kept(self):
        with self.assertRaises(isolated.IsolatedProcessError) as ctx:
            isolated.run_isolated(f'{TARGETS}:raise_unpicklable')
        msg = str(ctx.exception)
        self.assertIn('_Unpicklable: holds a file handle', msg)
        self.assertIn('could not be pickled', msg)
        self.assertIn('in raise_unpicklable', msg)

    def test_result_that_cannot_be_pickled___raises(self):
        with self.assertRaises(isolated.IsolatedProcessError) as ctx:
            isolated.run_isolated(f'{TARGETS}:return_unpicklable')
        self.assertIn('could not be pickled', str(ctx.exception))

    def test_prefork_pool_child___runs_in_process(self):
        with mock.patch.object(isolated, '_in_prefork_child', False):
            isolated._mark_prefork_child()  # what celery's worker_process_init does in prefork children
            self.assertFalse(isolated.isolation_enabled())
            self.assertEqual(isolated.run_isolated(f'{TARGETS}:add', 1)['pid'], os.getpid())
        self.assertTrue(isolated.isolation_enabled())

    def test_logs_and_output_reach_the_calling_thread(self):
        handler = _ListHandler()
        handler.addFilter(lambda r: r.thread == threading.get_ident())
        root = logging.getLogger()
        oasis_logger = logging.getLogger('oasislmf')
        old_level = oasis_logger.level
        root.addHandler(handler)
        oasis_logger.setLevel(logging.INFO)
        try:
            self.assertEqual(isolated.run_isolated(f'{TARGETS}:log_and_print'), 'ok')
        finally:
            root.removeHandler(handler)
            oasis_logger.setLevel(old_level)
        messages = [r.getMessage() for r in handler.records]
        self.assertIn('info from child', messages)
        self.assertNotIn('debug from child', messages)
        self.assertIn('printed by child', messages)
        self.assertIn('from a subprocess', messages)

    def test_cancel___kills_cpu_work_subprocesses_and_forked_workers(self):
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = os.path.join(tmp, 'pids.json')
            outcome = {}

            def task_thread():
                try:
                    isolated.run_isolated(f'{TARGETS}:busy_with_children', pid_file)
                except BaseException as e:
                    outcome['exc'] = e

            with mock.patch.object(isolated, '_current_task_id', return_value='isolated-tid'):
                t = threading.Thread(target=task_thread)
                t.start()
                end = time.time() + 30
                while not os.path.exists(pid_file) and time.time() < end:
                    time.sleep(0.1)
                pids = json.load(open(pid_file))
                for name, pid in pids.items():
                    self.assertTrue(_alive(pid), name)

                worker_state.revoked.add('isolated-tid')
                try:
                    t.join(15)
                finally:
                    worker_state.revoked.discard('isolated-tid')

            self.assertFalse(t.is_alive())
            self.assertIsInstance(outcome.get('exc'), Terminated)
            for name, pid in pids.items():
                self.assertFalse(_alive(pid), f'{name} ({pid}) still running after cancel')
