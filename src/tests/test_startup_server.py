import os
import socket
import subprocess
import sys
from unittest import TestCase
from unittest.mock import call, patch

from src import startup_server
from src.startup_server import PLAT2_MIGRATION_FALLBACK, main, manage, run_migrations, wait_for


def _completed(returncode=0, stdout=''):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout)


class WaitForTests(TestCase):
    def setUp(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(('127.0.0.1', 0))
        self.server.listen(1)
        self.port = self.server.getsockname()[1]

    def tearDown(self):
        self.server.close()

    def test_host_port_is_listening___returns(self):
        wait_for(f'127.0.0.1:{self.port}')

    def test_broker_url_with_credentials_and_vhost___waits_for_host_port(self):
        wait_for(f'amqp://user:pass@127.0.0.1:{self.port}/vhost')

    def test_url_without_credentials___waits_for_host_port(self):
        wait_for(f'redis://127.0.0.1:{self.port}/0')

    def test_url_with_at_sign_in_path___only_credentials_are_stripped(self):
        with patch('socket.create_connection') as create_connection:
            wait_for('amqp://user:pass@broker:5672/vh@st')

        create_connection.assert_called_once_with(('broker', 5672), timeout=1)

    def test_missing_port___exits_1(self):
        with self.assertRaises(SystemExit) as ctx:
            wait_for('127.0.0.1')
        self.assertEqual(ctx.exception.code, 1)

    def test_missing_host___exits_1(self):
        with self.assertRaises(SystemExit) as ctx:
            wait_for(':5432')
        self.assertEqual(ctx.exception.code, 1)

    def test_empty_address___exits_1(self):
        with self.assertRaises(SystemExit) as ctx:
            wait_for('')
        self.assertEqual(ctx.exception.code, 1)

    def test_non_numeric_port___exits_1(self):
        with self.assertRaises(SystemExit) as ctx:
            wait_for('db:port')
        self.assertEqual(ctx.exception.code, 1)

    def test_connection_refused_then_accepted___retries_until_available(self):
        with patch('socket.create_connection', side_effect=[OSError, OSError, socket.socket()]) as create_connection, \
                patch('time.sleep') as sleep:
            wait_for('db:5432', timeout=60)

        self.assertEqual(create_connection.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_never_available___exits_124_after_timeout(self):
        with patch('socket.create_connection', side_effect=OSError), \
                patch('time.monotonic', side_effect=[0, 1, 2, 3]), \
                patch('time.sleep') as sleep:
            with self.assertRaises(SystemExit) as ctx:
                wait_for('db:5432', timeout=3)

        self.assertEqual(ctx.exception.code, 124)
        self.assertEqual(sleep.call_count, 2)


class ManageTests(TestCase):
    def test_args_and_kwargs___passed_to_manage_py(self):
        with patch('subprocess.run', return_value=_completed()) as run:
            manage('migrate', 'files', capture_output=True)

        run.assert_called_once_with([sys.executable, 'manage.py', 'migrate', 'files'], capture_output=True)


class RunMigrationsTests(TestCase):
    def test_migrate_succeeds___no_fallback_run(self):
        with patch.object(startup_server, 'manage', return_value=_completed(0)) as manage_mock:
            run_migrations()

        manage_mock.assert_called_once_with('migrate')

    def test_migrate_fails_on_plat2_db___fallback_migrations_run(self):
        responses = [
            _completed(1),
            _completed(0, stdout=' [X] 0004_auto\n [ ] 0005_auto_20220510_1103\n'),
        ] + [_completed(0)] * len(PLAT2_MIGRATION_FALLBACK)

        with patch.object(startup_server, 'manage', side_effect=responses) as manage_mock:
            run_migrations()

        self.assertEqual(manage_mock.call_args_list, [
            call('migrate'),
            call('showmigrations', capture_output=True, text=True),
        ] + [call('migrate', *migration) for migration in PLAT2_MIGRATION_FALLBACK])

    def test_fallback_final_migrate_fails___exits_with_its_code(self):
        responses = [
            _completed(1),
            _completed(0, stdout=' [ ] 0005_auto_20220510_1103\n'),
        ] + [_completed(0)] * (len(PLAT2_MIGRATION_FALLBACK) - 1) + [_completed(3)]

        with patch.object(startup_server, 'manage', side_effect=responses):
            with self.assertRaises(SystemExit) as ctx:
                run_migrations()

        self.assertEqual(ctx.exception.code, 3)

    def test_migrate_fails_not_plat2_db___exits_without_fallback(self):
        responses = [
            _completed(2),
            _completed(0, stdout=' [X] 0005_auto_20220510_1103\n'),
        ]

        with patch.object(startup_server, 'manage', side_effect=responses) as manage_mock:
            with self.assertRaises(SystemExit) as ctx:
                run_migrations()

        self.assertEqual(ctx.exception.code, 2)
        self.assertEqual(manage_mock.call_count, 2)


class MainTests(TestCase):
    ENV = {
        'OASIS_SERVER_DB_HOST': 'server-db',
        'OASIS_SERVER_DB_PORT': '5432',
        'OASIS_CELERY_DB_HOST': 'celery-db',
        'OASIS_CELERY_DB_PORT': '5433',
        'OASIS_CELERY_BROKER_URL': 'amqp://rabbit:rabbit@broker:5672',
    }

    def setUp(self):
        patchers = {
            'wait_for': patch.object(startup_server, 'wait_for'),
            'run_migrations': patch.object(startup_server, 'run_migrations'),
            'subprocess_run': patch('subprocess.run', return_value=_completed(0)),
            'execvp': patch('os.execvp'),
            'argv': patch.object(sys, 'argv', ['startup']),
            'environ': patch.dict(os.environ, self.ENV),
        }
        self.mocks = {}
        for name, patcher in patchers.items():
            self.mocks[name] = patcher.start()
            self.addCleanup(patcher.stop)
        os.environ.pop('STARTUP_RUN_MIGRATIONS', None)

    def test_waits_for_dbs_and_broker(self):
        main()

        self.assertEqual(self.mocks['wait_for'].call_args_list, [
            call('server-db:5432'),
            call('celery-db:5433'),
            call('amqp://rabbit:rabbit@broker:5672'),
        ])
        self.assertEqual(os.environ['OASIS_API_INI_PATH'], './conf.ini')

    def test_migrations_not_set___not_run(self):
        main()

        self.mocks['run_migrations'].assert_not_called()

    def test_migrations_true___run(self):
        os.environ['STARTUP_RUN_MIGRATIONS'] = 'true'
        main()

        self.mocks['run_migrations'].assert_called_once_with()

    def test_migrations_other_value___not_run(self):
        os.environ['STARTUP_RUN_MIGRATIONS'] = 'false'
        main()

        self.mocks['run_migrations'].assert_not_called()

    def test_set_default_user___run_with_current_python(self):
        main()

        self.mocks['subprocess_run'].assert_called_once_with([sys.executable, 'set_default_user.py'])

    def test_set_default_user_fails___exits_before_exec(self):
        self.mocks['subprocess_run'].return_value = _completed(5)
        sys.argv = ['startup', './wsgi/run-wsgi.py']

        with self.assertRaises(SystemExit) as ctx:
            main()

        self.assertEqual(ctx.exception.code, 5)
        self.mocks['execvp'].assert_not_called()

    def test_command_given___execs_command(self):
        sys.argv = ['startup', './wsgi/run-wsgi.py', '--some-arg']
        main()

        self.mocks['execvp'].assert_called_once_with('./wsgi/run-wsgi.py', ['./wsgi/run-wsgi.py', '--some-arg'])

    def test_no_command___returns_without_exec(self):
        main()

        self.mocks['execvp'].assert_not_called()
