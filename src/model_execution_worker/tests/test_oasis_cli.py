import json
import logging
import os
import signal
import sys
import tempfile
import threading
import time
from unittest import TestCase, mock

import celery
import psutil
from celery.concurrency.prefork import TaskPool as PreforkPool
from celery.concurrency.thread import TaskPool as ThreadPool
from celery.exceptions import Terminated
from celery.worker import state as worker_state
from oasislmf.utils.exceptions import OasisExceptionNoKeys

from src.model_execution_worker import oasis_cli

FAKE_CLI = os.path.join(os.path.dirname(__file__), 'fake_oasislmf_cli.py')


def _fake_argv(command, config_fp):
    return [sys.executable, FAKE_CLI, command, config_fp]


def _alive(pid):
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def _wait_for_file(path, timeout=30):
    end = time.time() + timeout
    while not os.path.exists(path) and time.time() < end:
        time.sleep(0.05)
    return os.path.exists(path)


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


class PoolDetectionTests(TestCase):

    def test_in_process_pools(self):
        for pool in ('threads', 'gevent', 'eventlet', ThreadPool):
            self.assertTrue(oasis_cli._is_in_process_pool(pool), pool)

    def test_other_pools(self):
        for pool in ('prefork', 'processes', 'solo', PreforkPool, None):
            self.assertFalse(oasis_cli._is_in_process_pool(pool), pool)

    def test_worker_init_records_pool(self):
        with mock.patch.object(oasis_cli, '_pool_in_process', False):
            oasis_cli._record_worker_pool(sender=mock.Mock(pool_cls='threads'))
            self.assertTrue(oasis_cli._pool_in_process)
            oasis_cli._record_worker_pool(sender=mock.Mock(pool_cls='prefork'))
            self.assertFalse(oasis_cli._pool_in_process)


class RoutingTests(TestCase):

    def test_default___manager_is_called(self):
        with mock.patch.object(oasis_cli, '_pool_in_process', False), \
                mock.patch('oasislmf.manager.OasisManager') as manager, \
                mock.patch.object(oasis_cli, 'run_cli') as run_cli:
            oasis_cli.run_oasis_manager('generate_oasis_files', a=1)
        manager.return_value.generate_oasis_files.assert_called_once_with(a=1)
        run_cli.assert_not_called()

    def test_in_process_pool___cli_is_used(self):
        with mock.patch.object(oasis_cli, '_pool_in_process', True), \
                mock.patch('oasislmf.manager.OasisManager') as manager, \
                mock.patch.object(oasis_cli, 'run_cli') as run_cli:
            oasis_cli.run_oasis_manager('generate_losses_partial', a=1)
        run_cli.assert_called_once_with('generate-losses-chunk', {'a': 1})
        manager.assert_not_called()

    def test_in_process_pool_but_no_cli_command___manager_is_called(self):
        with mock.patch.object(oasis_cli, '_pool_in_process', True), \
                mock.patch('oasislmf.manager.OasisManager') as manager, \
                mock.patch.object(oasis_cli, 'run_cli') as run_cli:
            manager.return_value.generate_losses_dir.return_value = {'settings': 1}
            self.assertEqual(oasis_cli.run_oasis_manager('generate_losses_dir', a=1), {'settings': 1})
        run_cli.assert_not_called()

    def test_env_override(self):
        with mock.patch.object(oasis_cli, '_pool_in_process', False):
            with mock.patch.dict(os.environ, {'OASIS_WORKER_CLI_EXECUTION': 'true'}):
                self.assertTrue(oasis_cli.cli_enabled())
        with mock.patch.object(oasis_cli, '_pool_in_process', True):
            with mock.patch.dict(os.environ, {'OASIS_WORKER_CLI_EXECUTION': 'false'}):
                self.assertFalse(oasis_cli.cli_enabled())
            with mock.patch.dict(os.environ, {'OASIS_WORKER_CLI_EXECUTION': 'auto'}):
                self.assertTrue(oasis_cli.cli_enabled())


@mock.patch.object(oasis_cli, '_cli_argv', _fake_argv)
@mock.patch.dict(os.environ, {'OASIS_WORKER_TASK_CANCEL_POLL_INTERVAL': '0.2',
                              'OASIS_WORKER_TASK_CANCEL_KILL_TIMEOUT': '2'})
class RunCliTests(TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pid_file = os.path.join(self.tmp.name, 'pids.json')

    def tearDown(self):
        worker_state.revoked.discard('cli-tid')
        self.tmp.cleanup()

    def test_success___params_passed_as_config_and_output_logged_in_calling_thread(self):
        handler = _ListHandler()
        handler.addFilter(lambda r: r.thread == threading.get_ident())
        cli_logger = logging.getLogger('oasislmf.cli')
        old_level = cli_logger.level
        cli_logger.addHandler(handler)
        cli_logger.setLevel(logging.INFO)
        try:
            self.assertIsNone(oasis_cli.run_cli('generate-losses', {'mode': 'ok', 'model_run_dir': '/tmp/x'}))
        finally:
            cli_logger.removeHandler(handler)
            cli_logger.setLevel(old_level)
        self.assertIn('command=generate-losses', handler.messages)
        self.assertIn('config={"mode": "ok", "model_run_dir": "/tmp/x"}', handler.messages)
        self.assertIn('COMPLETED: run', handler.messages)

    def test_failure___raises_with_output(self):
        with self.assertRaises(oasis_cli.OasisCLIError) as ctx:
            oasis_cli.run_cli('generate-losses', {'mode': 'fail'})
        self.assertIn('exit code 3', str(ctx.exception))
        self.assertIn('Something went wrong', str(ctx.exception))

    def test_no_keys___raises_oasis_no_keys_exception(self):
        with self.assertRaises(OasisExceptionNoKeys):
            oasis_cli.run_cli('generate-oasis-files', {'mode': 'no_keys'})

    def test_background_process_left_after_success___is_stopped(self):
        oasis_cli.run_cli('generate-losses', {'mode': 'leave_background', 'pid_file': self.pid_file})
        self.assertTrue(_wait_for_file(self.pid_file))
        pid = int(open(self.pid_file).read())
        self.assertFalse(_alive(pid))

    def _run_busy_in_thread(self):
        outcome = {}

        def task_thread():
            try:
                oasis_cli.run_cli('generate-losses', {'mode': 'busy', 'pid_file': self.pid_file})
            except BaseException as e:
                outcome['exc'] = e

        t = threading.Thread(target=task_thread)
        t.start()
        self.assertTrue(_wait_for_file(self.pid_file))
        pids = json.load(open(self.pid_file))
        for name, pid in pids.items():
            self.assertTrue(_alive(pid), name)
        return t, pids, outcome

    def test_cancel___kills_cli_bash_children_and_forked_workers(self):
        with mock.patch.object(celery, 'current_task', mock.Mock(request=mock.Mock(id='cli-tid'))):
            t, pids, outcome = self._run_busy_in_thread()
            worker_state.revoked.add('cli-tid')
            t.join(20)
        self.assertFalse(t.is_alive())
        self.assertIsInstance(outcome.get('exc'), Terminated)
        for name, pid in pids.items():
            self.assertFalse(_alive(pid), f'{name} ({pid}) still running after cancel')

    def test_cancel_where_process_is_killed_by_someone_else_first___still_terminated(self):
        # e.g. the task_cancel watcher killing it before run_cli's own poll sees the revoke
        with mock.patch.object(celery, 'current_task', mock.Mock(request=mock.Mock(id='cli-tid'))):
            t, pids, outcome = self._run_busy_in_thread()
            worker_state.revoked.add('cli-tid')
            os.killpg(pids['cli'], signal.SIGKILL)
            t.join(20)
        self.assertIsInstance(outcome.get('exc'), Terminated)
        for name, pid in pids.items():
            self.assertFalse(_alive(pid), name)
