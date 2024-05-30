import os
import tarfile
import json
from unittest import TestCase
from contextlib import contextmanager

from backports.tempfile import TemporaryDirectory
from celery.exceptions import Retry
from hypothesis import given
from hypothesis import settings as hypothesis_settings
from hypothesis.strategies import text, integers
from mock import patch, Mock, ANY
from pathlib2 import Path

from src.conf.iniconf import SettingsPatcher
from src.model_execution_worker.storage_manager import MissingInputsException
from src.model_execution_worker.tasks import start_analysis, InvalidInputsException, \
    start_analysis_task


# from oasislmf.utils.status import OASIS_TASK_STATUS
OASIS_TASK_STATUS = {
    'pending': {'id': 'PENDING', 'desc': 'Pending'},
    'running': {'id': 'RUNNING', 'desc': 'Running'},
    'success': {'id': 'SUCCESS', 'desc': 'Success'},
    'failure': {'id': 'FAILURE', 'desc': 'Failure'}
}

# Override default deadline for all tests to 8s
hypothesis_settings.register_profile("ci", deadline=800.0)
hypothesis_settings.load_profile("ci")


class StartAnalysis(TestCase):
    def create_tar(self, target):
        with TemporaryDirectory() as media_root, tarfile.open(target, 'w') as tar:
            paths = [
                Path(media_root, 'events.bin'),
                Path(media_root, 'returnperiods.bin'),
                Path(media_root, 'occurrence.bin'),
                Path(media_root, 'periods.bin'),
            ]

            for path in paths:
                path.touch()
                tar.add(str(path), path.name)

    def test_input_tar_file_does_not_exist___exception_is_raised(self):
        with TemporaryDirectory() as media_root:
            with SettingsPatcher(MEDIA_ROOT=media_root):
                Path(media_root, 'analysis_settings.json').touch()
                with self.assertRaises(MissingInputsException):
                    start_analysis(
                        input_location=os.path.join(media_root, 'non-existant-location.tar'),
                        analysis_settings=os.path.join(media_root, 'analysis_settings.json')
                    )

    def test_settings_file_does_not_exist___exception_is_raised(self):
        with TemporaryDirectory() as media_root:
            with SettingsPatcher(MEDIA_ROOT=media_root):
                self.create_tar(str(Path(media_root, 'location.tar')))
                with self.assertRaises(MissingInputsException):
                    start_analysis(
                        input_location=os.path.join(media_root, 'location.tar'),
                        analysis_settings=os.path.join(media_root, 'analysis_settings.json')
                    )

    def test_input_location_is_not_a_tar___exception_is_raised(self):
        with TemporaryDirectory() as media_root:
            with SettingsPatcher(MEDIA_ROOT=media_root):
                Path(media_root, 'not-tar-file.tar').touch()
                Path(media_root, 'analysis_settings.json').touch()
                self.assertRaises(InvalidInputsException, start_analysis,
                                  os.path.join(media_root, 'analysis_settings.json'),
                                  os.path.join(media_root, 'not-tar-file.tar')
                                  )

    def test_custom_model_runner_does_not_exist___generate_losses_is_called_output_files_are_tared_up(self):
        with TemporaryDirectory() as media_root, \
                TemporaryDirectory() as model_data_dir, \
                TemporaryDirectory() as run_dir, \
                TemporaryDirectory() as log_dir, \
                TemporaryDirectory() as work_dir:
            with SettingsPatcher(
                    MODEL_SUPPLIER_ID='supplier',
                    MODEL_ID='model',
                    MODEL_VERSION_ID='version',
                    MEDIA_ROOT=media_root,
                    MODEL_DATA_DIRECTORY=model_data_dir,
                    WORKING_DIRECTORY=work_dir,):
                self.create_tar(str(Path(media_root, 'location.tar')))
                Path(media_root, 'analysis_settings.json').touch()
                Path(run_dir, 'output').mkdir(parents=True)
                Path(model_data_dir, 'supplier', 'model', 'version').mkdir(parents=True)
                log_file = Path(log_dir, 'log-file.log').touch()

                params = {
                    "oasis_files_dir": os.path.join(run_dir, 'input'),
                    "model_run_dir": run_dir,
                    "ktools_fifo_relative": True,
                    "verbose": False
                }
                with open(Path(model_data_dir, 'oasislmf.json'), 'w') as f:
                    f.write(json.dumps(params))

                cmd_instance = Mock()

                @contextmanager
                def fake_run_dir(*args, **kwargs):
                    yield run_dir

                with patch('oasislmf.manager.OasisManager.generate_oasis_losses', Mock(return_value='mocked result')) as cmd_mock, \
                        patch('src.model_execution_worker.tasks.get_worker_versions', Mock(return_value='')), \
                        patch('src.model_execution_worker.tasks.filestore.compress') as tarfile, \
                        patch('src.model_execution_worker.tasks.TASK_LOG_DIR', log_dir), \
                        patch('src.model_execution_worker.tasks.TemporaryDir', fake_run_dir):

                    output_location, log_location, error_location, returncode = start_analysis(
                        os.path.join(media_root, 'analysis_settings.json'),
                        os.path.join(media_root, 'location.tar'),
                        log_filename=log_file,
                    )

                    cmd_mock.assert_called_once()
                    called_args = cmd_mock.call_args.kwargs
                    self.assertEqual(called_args.get('oasis_files_dir', None), params.get('oasis_files_dir'))
                    self.assertEqual(called_args.get('model_run_dir', None), params.get('model_run_dir'))
                    self.assertEqual(called_args.get('ktools_fifo_relative', None), params.get('ktools_fifo_relative'))
                    self.assertEqual(called_args.get('verbose', None), params.get('verbose'))
                    self.assertEqual(called_args.get('analysis_settings.json', None), params.get('analysis_settings.json'))
                    tarfile.assert_called_once_with(ANY, os.path.join(run_dir, 'output'), 'output')


class StartAnalysisTask(TestCase):
    @given(pk=integers(), location=text(), analysis_settings_path=text())
    def test_lock_is_not_acquireable___retry_esception_is_raised(self, pk, location, analysis_settings_path):
        with TemporaryDirectory() as log_dir:
            with patch('fasteners.InterProcessLock.acquire', Mock(return_value=False)), \
                    patch('src.model_execution_worker.tasks.check_worker_lost', Mock(return_value='')), \
                    patch('src.model_execution_worker.tasks.TASK_LOG_DIR', log_dir), \
                    patch('src.model_execution_worker.tasks.notify_api_status') as api_notify:

                with self.assertRaises(Retry):
                    start_analysis_task(pk, location, analysis_settings_path)

    @given(pk=integers(), location=text(), analysis_settings_path=text())
    def test_lock_is_acquireable___start_analysis_is_ran(self, pk, location, analysis_settings_path):
        with TemporaryDirectory() as log_dir:
            with patch('src.model_execution_worker.tasks.start_analysis', Mock(return_value=('', '', '', 0))) as start_analysis_mock, \
                    patch('src.model_execution_worker.tasks.check_worker_lost', Mock(return_value='')), \
                    patch('src.model_execution_worker.tasks.TASK_LOG_DIR', log_dir), \
                    patch('src.model_execution_worker.tasks.notify_api_status') as api_notify:

                start_analysis_task.update_state = Mock()
                start_analysis_task(pk, location, analysis_settings_path)

                api_notify.assert_called_once_with(pk, 'RUN_STARTED')
                start_analysis_task.update_state.assert_called_once_with(state=OASIS_TASK_STATUS["running"]["id"])
                start_analysis_mock.assert_called_once_with(
                    analysis_settings_path,
                    location,
                    complex_data_files=None,
                    log_filename=f'{log_dir}/analysis_{pk}_None.log'
                )
