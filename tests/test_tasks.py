import os
import tarfile
from unittest import TestCase

from backports.tempfile import TemporaryDirectory
from celery.exceptions import Retry
from hypothesis import given
from hypothesis import settings as hypothesis_settings
from hypothesis.strategies import text
from mock import patch, Mock, ANY
from oasislmf.utils.status import OASIS_TASK_STATUS
from pathlib2 import Path

from src.conf.iniconf import SettingsPatcher, settings
from src.model_execution_worker.tasks import start_analysis, InvalidInputsException, MissingInputsException, \
    start_analysis_task, get_oasislmf_config_path

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
                self.assertRaises(MissingInputsException, start_analysis, {}, 'non-existant-location.tar')

    def test_input_location_is_not_a_tar___exception_is_raised(self):
        with TemporaryDirectory() as media_root:
            with SettingsPatcher(MEDIA_ROOT=media_root):
                Path(media_root, 'not-tar-file.tar').touch()

                self.assertRaises(InvalidInputsException, start_analysis, {}, 'not-tar-file.tar')

    def test_custom_model_runner_does_not_exist___generate_losses_is_called_output_files_are_tared_up(self):
        with TemporaryDirectory() as media_root, \
                TemporaryDirectory() as model_data_dir, \
                TemporaryDirectory() as work_dir:
            with SettingsPatcher(
                    MODEL_SUPPLIER_ID='supplier',
                    MODEL_ID='model',
                    MODEL_VERSION_ID='version',
                    MEDIA_ROOT=media_root,
                    MODEL_DATA_DIRECTORY=model_data_dir,
                    WORKING_DIRECTORY=work_dir,):
                self.create_tar(str(Path(media_root, 'location.tar')))
                Path(model_data_dir, 'supplier', 'model', 'version').mkdir(parents=True)

                cmd_instance = Mock()
                with patch('src.model_execution_worker.tasks.GenerateLossesCmd', Mock(return_value=cmd_instance)) as cmd_mock, \
                        patch('src.model_execution_worker.tasks.tarfile') as tarfile:
                    output_location = start_analysis(
                        'analysis_settings.json',
                        'location.tar',
                    )
                    cmd_mock.assert_called_once_with(argv=[
                        '--oasis-files-path', ANY,
                        '--config', get_oasislmf_config_path(settings.get('worker', 'model_id')),
                        '--model-run-dir', ANY,
                        '--analysis-settings-file-path', 'analysis_settings.json',
                        '--ktools-num-processes', settings.get('worker', 'KTOOLS_BATCH_COUNT'),
                        '--ktools-alloc-rule-gul', settings.get('worker', 'KTOOLS_ALLOC_RULE_GUL'),
                        '--ktools-alloc-rule-il', settings.get('worker', 'KTOOLS_ALLOC_RULE_IL'),
                        '--ktools-fifo-relative',
                        '--verbose'
                    ])
                    cmd_instance.run.assert_called_once_with()
                    self.assertEqual(tarfile.open.call_args_list[1][0], (str(Path(media_root, output_location)), 'w:gz'))


class StartAnalysisTask(TestCase):
    @given(location=text(), analysis_settings_path=text())
    def test_lock_is_not_acquireable___retry_esception_is_raised(self, location, analysis_settings_path):
        with patch('fasteners.InterProcessLock.acquire', Mock(return_value=False)):
            with self.assertRaises(Retry):
                start_analysis_task(location, analysis_settings_path)

    @given(location=text(), analysis_settings_path=text())
    def test_lock_is_acquireable___start_analysis_is_ran(self, location, analysis_settings_path):
        with patch('src.model_execution_worker.tasks.start_analysis', Mock(return_value=True)) as start_analysis_mock:
            start_analysis_task.update_state = Mock()
            start_analysis_task(location, analysis_settings_path)

            start_analysis_task.update_state.assert_called_once_with(state=OASIS_TASK_STATUS["running"]["id"])
            start_analysis_mock.assert_called_once_with(
                os.path.join(settings.get('worker', 'media_root'), analysis_settings_path),
                location,
                complex_data_files=None
            )
