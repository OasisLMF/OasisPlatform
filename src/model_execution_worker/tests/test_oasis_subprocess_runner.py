import json
import logging
import os
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

from src.model_execution_worker import oasis_subprocess_runner, utils

FAKE_MANAGER = 'src.model_execution_worker.tests.fake_oasis_manager:FakeManager'
FAKE_FUNCTION = 'src.model_execution_worker.tests.fake_oasis_manager:add'


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
            self.assertTrue(oasis_subprocess_runner._is_in_process_pool(pool), pool)

    def test_other_pools(self):
        for pool in ('prefork', 'processes', 'solo', PreforkPool, None):
            self.assertFalse(oasis_subprocess_runner._is_in_process_pool(pool), pool)

    def test_worker_init_records_pool(self):
        with mock.patch.object(oasis_subprocess_runner, '_pool_in_process', False):
            oasis_subprocess_runner._record_worker_pool(sender=mock.Mock(pool_cls='threads'))
            self.assertTrue(oasis_subprocess_runner._pool_in_process)
            oasis_subprocess_runner._record_worker_pool(sender=mock.Mock(pool_cls='prefork'))
            self.assertFalse(oasis_subprocess_runner._pool_in_process)


class RoutingTests(TestCase):

    def test_default___manager_is_called_in_process(self):
        with mock.patch.object(oasis_subprocess_runner, '_pool_in_process', False), \
                mock.patch('oasislmf.manager.OasisManager') as manager, \
                mock.patch.object(utils, 'run_in_subprocess') as run_in_subprocess:
            manager.return_value.generate_losses_dir.return_value = {'settings': 1}
            self.assertEqual(utils.run_oasis('generate_losses_dir', a=1), {'settings': 1})
        manager.return_value.generate_losses_dir.assert_called_once_with(a=1)
        run_in_subprocess.assert_not_called()

    def test_in_process_pool___subprocess_is_used(self):
        with mock.patch.object(oasis_subprocess_runner, '_pool_in_process', True), \
                mock.patch('oasislmf.manager.OasisManager') as manager, \
                mock.patch.object(utils, 'run_in_subprocess', return_value={'settings': 1}) as run_in_subprocess:
            self.assertEqual(utils.run_oasis('generate_losses_dir', a=1), {'settings': 1})
        run_in_subprocess.assert_called_once_with(oasis_subprocess_runner.MANAGER, {'a': 1}, method='generate_losses_dir')
        manager.assert_not_called()

    def test_run_function___in_process_gets_in_process_only_kwargs(self):
        func = mock.Mock(__module__='some.module', __qualname__='func', return_value=3)
        with mock.patch.object(oasis_subprocess_runner, '_pool_in_process', False), \
                mock.patch.object(utils, 'run_in_subprocess') as run_in_subprocess:
            self.assertEqual(utils.run_function(func, in_process_only={'filestore': 'fs'}, a=1), 3)
        func.assert_called_once_with(a=1, filestore='fs')
        run_in_subprocess.assert_not_called()

    def test_run_function___subprocess_gets_import_path_and_json_kwargs_only(self):
        func = mock.Mock(__module__='some.module', __qualname__='func')
        with mock.patch.object(oasis_subprocess_runner, '_pool_in_process', True), \
                mock.patch.object(utils, 'run_in_subprocess', return_value=3) as run_in_subprocess:
            self.assertEqual(utils.run_function(func, in_process_only={'filestore': 'fs'}, a=1), 3)
        run_in_subprocess.assert_called_once_with('some.module:func', {'a': 1})
        func.assert_not_called()

    def _enabled(self, setting, pool_in_process):
        env = {k: v for k, v in os.environ.items() if k != 'OASIS_WORKER_SUBPROCESS_EXECUTION'}
        if setting is not None:
            env['OASIS_WORKER_SUBPROCESS_EXECUTION'] = setting
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(oasis_subprocess_runner, '_pool_in_process', pool_in_process):
            return oasis_subprocess_runner.subprocess_enabled()

    def test_default___on_for_in_process_pools_only(self):
        for setting in (None, '', 'auto', ' AUTO '):
            self.assertTrue(self._enabled(setting, pool_in_process=True), setting)
            self.assertFalse(self._enabled(setting, pool_in_process=False), setting)

    def test_env_var___overrides_the_pool(self):
        for setting in ('true', 'True', '1', 'yes', 'on'):
            self.assertTrue(self._enabled(setting, pool_in_process=False), setting)
        for setting in ('false', 'FALSE', '0', 'no', 'off'):
            self.assertFalse(self._enabled(setting, pool_in_process=True), setting)

    def test_conf_ini_setting___used_when_env_var_not_set(self):
        oasis_subprocess_runner.settings.set('worker', 'SUBPROCESS_EXECUTION', 'true')
        try:
            self.assertTrue(self._enabled(None, pool_in_process=False))
            self.assertFalse(self._enabled('false', pool_in_process=False))  # env var wins
        finally:
            oasis_subprocess_runner.settings.remove_option('worker', 'SUBPROCESS_EXECUTION')

    def test_unknown_value___warns_once_and_uses_pool_default(self):
        with mock.patch.object(oasis_subprocess_runner, '_warned_values', set()), \
                self.assertLogs(oasis_subprocess_runner.logger, 'WARNING') as logs:
            self.assertTrue(self._enabled('ture', pool_in_process=True))
            self.assertFalse(self._enabled('ture', pool_in_process=False))
        self.assertEqual(len(logs.records), 1)
        self.assertIn("'ture'", logs.output[0])

    def test_worker_start___logs_the_decision(self):
        with mock.patch.dict(os.environ, {'OASIS_WORKER_SUBPROCESS_EXECUTION': 'auto'}), \
                mock.patch.object(oasis_subprocess_runner, '_pool_in_process', False), \
                self.assertLogs(oasis_subprocess_runner.logger, 'INFO') as logs:
            oasis_subprocess_runner._record_worker_pool(sender=mock.Mock(pool_cls='threads'))
            oasis_subprocess_runner._log_subprocess_execution()
        self.assertIn('Subprocess execution: on (pool=threads, SUBPROCESS_EXECUTION=auto)', logs.output[0])


@mock.patch.dict(os.environ, {'OASIS_WORKER_TASK_CANCEL_POLL_INTERVAL': '0.2',
                              'OASIS_WORKER_TASK_CANCEL_KILL_TIMEOUT': '2'})
class RunInSubprocessTests(TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pid_file = os.path.join(self.tmp.name, 'pids.json')

    def tearDown(self):
        worker_state.revoked.discard('runner-tid')
        self.tmp.cleanup()

    def test_success___returns_value_and_logs_output_in_calling_thread(self):
        handler = _ListHandler()
        handler.addFilter(lambda r: r.thread == threading.get_ident())
        output_logger = oasis_subprocess_runner.output_logger
        old_level = output_logger.level
        output_logger.addHandler(handler)
        output_logger.setLevel(logging.INFO)
        try:
            with mock.patch.object(oasis_subprocess_runner, '_log_level', return_value='INFO'):
                result = oasis_subprocess_runner.run_in_subprocess(FAKE_MANAGER, {'model_run_dir': '/tmp/x', 'n': 2}, method='ok')
        finally:
            output_logger.removeHandler(handler)
            output_logger.setLevel(old_level)
        self.assertEqual(result, {'kwargs': {'model_run_dir': '/tmp/x', 'n': 2}, 'path': '/tmp/x'})
        self.assertIn('running ok', handler.messages)

    def test_function_target___runs_in_child_and_returns_value(self):
        result = oasis_subprocess_runner.run_in_subprocess(FAKE_FUNCTION, {'a': 2, 'b': 3})
        self.assertEqual(result['sum'], 5)
        self.assertNotEqual(result['pid'], os.getpid())

    def test_failure___raises_with_type_and_child_traceback(self):
        with self.assertRaises(oasis_subprocess_runner.OasisRunnerError) as ctx:
            oasis_subprocess_runner.run_in_subprocess(FAKE_MANAGER, {}, method='fail')
        self.assertIn('builtins.ValueError: Something went wrong', str(ctx.exception))
        self.assertIn('fake_oasis_manager.py', str(ctx.exception))

    def test_client_exception_that_cant_be_imported___keeps_message_and_traceback(self):
        with self.assertRaises(oasis_subprocess_runner.OasisRunnerError) as ctx:
            oasis_subprocess_runner.run_in_subprocess(FAKE_MANAGER, {}, method='client_error')
        self.assertIn('ClientLookupError: bad lookup data', str(ctx.exception))
        self.assertIn('raise ClientLookupError', str(ctx.exception))

    def test_no_keys___raises_oasis_no_keys_exception(self):
        with self.assertRaises(OasisExceptionNoKeys):
            oasis_subprocess_runner.run_in_subprocess(FAKE_MANAGER, {}, method='no_keys')

    def test_child_dies_without_result___raises_with_exit_code_and_output(self):
        with self.assertRaises(oasis_subprocess_runner.OasisRunnerError) as ctx:
            oasis_subprocess_runner.run_in_subprocess(FAKE_MANAGER, {}, method='crash')
        self.assertIn('exited with code 9 without a result', str(ctx.exception))
        self.assertIn('about to crash', str(ctx.exception))

    def test_background_process_left_after_success___is_stopped(self):
        oasis_subprocess_runner.run_in_subprocess(FAKE_MANAGER, {'pid_file': self.pid_file}, method='leave_background')
        self.assertTrue(_wait_for_file(self.pid_file))
        pid = int(open(self.pid_file).read())
        self.assertFalse(_alive(pid))

    def test_cancel___kills_runner_bash_children_and_forked_workers(self):
        outcome = {}

        def task_thread():
            try:
                oasis_subprocess_runner.run_in_subprocess(FAKE_MANAGER, {'pid_file': self.pid_file}, method='busy')
            except BaseException as e:
                outcome['exc'] = e

        with mock.patch.object(celery, 'current_task', mock.Mock(request=mock.Mock(id='runner-tid'))):
            t = threading.Thread(target=task_thread)
            t.start()
            self.assertTrue(_wait_for_file(self.pid_file))
            pids = json.load(open(self.pid_file))
            for name, pid in pids.items():
                self.assertTrue(_alive(pid), name)
            worker_state.revoked.add('runner-tid')
            t.join(20)
        self.assertFalse(t.is_alive())
        self.assertIsInstance(outcome.get('exc'), Terminated)
        for name, pid in pids.items():
            self.assertFalse(_alive(pid), f'{name} ({pid}) still running after cancel')
