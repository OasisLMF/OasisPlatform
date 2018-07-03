import tarfile
from unittest import TestCase

import os
from backports.tempfile import TemporaryDirectory
from celery.exceptions import Retry
from hypothesis import given
from hypothesis.strategies import text, dictionaries
from mock import patch, Mock
from oasislmf.utils import status
from pathlib2 import Path

from src.conf.iniconf import SettingsPatcher, settings
from src.model_execution_worker.tasks import start_analysis, InvalidInputsException, MissingInputsException, \
    MissingModelDataException, start_analysis_task


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

    def test_input_model_data_does_not_exist___exception_is_raised(self):
        with TemporaryDirectory() as media_root, TemporaryDirectory() as model_data_dir:
            with SettingsPatcher(
                    MODEL_SUPPLIER_ID='supplier',
                    MODEL_ID='model',
                    MODEL_VERSION_ID='version',
                    MEDIA_ROOT=media_root,
                    MODEL_DATA_DIRECTORY=model_data_dir):
                self.create_tar(str(Path(media_root, 'location.tar')))

                self.assertRaises(
                    MissingModelDataException,
                    start_analysis,
                    {'analysis_settings': {
                        'source_tag': 'source',
                        'analysis_tag': 'source',
                    }},
                    'location.tar',
                )

    def test_custom_model_runner_does_not_exist___default_runner_is_used(self):
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

                with patch('src.model_execution_worker.tasks.runner') as default_mock:
                    start_analysis({
                        'analysis_settings': {
                            'source_tag': 'source',
                            'analysis_tag': 'source',
                        }},
                        'location.tar',
                    )
                    default_mock.run.assert_called_once_with(
                        {
                            'source_tag': 'source',
                            'analysis_tag': 'source',
                        },
                        settings.getint('worker', 'KTOOLS_BATCH_COUNT'),
                        num_reinsurance_iterations=0
                    )

    def test_custom_model_runner_exists___custom_runner_is_used(self):
        with TemporaryDirectory() as media_root, \
                TemporaryDirectory() as model_data_dir, \
                TemporaryDirectory() as work_dir, \
                TemporaryDirectory() as module_dir:
            with SettingsPatcher(
                    MODEL_SUPPLIER_ID='supplier',
                    MODEL_ID='model',
                    MODEL_VERSION_ID='version',
                    MEDIA_ROOT=media_root,
                    MODEL_DATA_DIRECTORY=model_data_dir,
                    WORKING_DIRECTORY=work_dir,
                    SUPPLIER_MODULE_DIRECTORY=module_dir):
                self.create_tar(str(Path(media_root, 'location.tar')))

                Path(model_data_dir, 'supplier', 'model', 'version').mkdir(parents=True)
                Path(module_dir, 'supplier').mkdir()
                Path(module_dir, 'supplier', '__init__.py').touch()
                with open(str(Path(module_dir, 'supplier').joinpath('supplier_model_runner.py')), 'w') as module:
                    module.writelines([
                        'from pathlib2 import Path\n',
                        'def run(settings, location, num_reinsurance_iterations):\n',
                        '    Path("{}", "custom_model").touch()\n'.format(out_dir)
                    ])

                start_analysis({
                    'analysis_settings': {
                        'source_tag': 'source',
                        'analysis_tag': 'source',
                    }},
                    'location.tar',
                )
                self.assertTrue(Path(media_root, "custom_model").exists())

    def test_do_clear_working_is_true___working_directory_is_removed_after_run(self):
        with TemporaryDirectory() as media_root, \
                TemporaryDirectory() as model_data_dir, \
                TemporaryDirectory() as work_dir:
            with SettingsPatcher(
                    MODEL_SUPPLIER_ID='supplier',
                    MODEL_ID='model',
                    MODEL_VERSION_ID='version',
                    MEDIA_ROOT=media_root,
                    MODEL_DATA_DIRECTORY=model_data_dir,
                    WORKING_DIRECTORY=work_dir,
                    DO_CLEAr_WORKING='True'):
                self.create_tar(str(Path(media_root, 'location.tar')))
                Path(model_data_dir, 'supplier', 'model', 'version').mkdir(parents=True)

                with patch('src.model_execution_worker.tasks.runner'):
                    start_analysis({
                        'analysis_settings': {
                            'source_tag': 'source',
                            'analysis_tag': 'source',
                        }},
                        'location.tar',
                    )

                self.assertEqual(0, len(os.listdir(work_dir)))

    def test_do_clear_working_is_false___working_directory_is_not_removed_after_run(self):
        with TemporaryDirectory() as media_root, \
                TemporaryDirectory() as model_data_dir, \
                TemporaryDirectory() as work_dir:
            with SettingsPatcher(
                    MODEL_SUPPLIER_ID='supplier',
                    MODEL_ID='model',
                    MODEL_VERSION_ID='version',
                    MEDIA_ROOT=media_root,
                    MODEL_DATA_DIRECTORY=model_data_dir,
                    WORKING_DIRECTORY=work_dir,
                    DO_CLEAr_WORKING='False'):
                self.create_tar(str(Path(media_root, 'location.tar')))
                Path(model_data_dir, 'supplier', 'model', 'version').mkdir(parents=True)

                with patch('src.model_execution_worker.tasks.runner'):
                    start_analysis({
                        'analysis_settings': {
                            'source_tag': 'source',
                            'analysis_tag': 'source',
                        }},
                        'location.tar',
                    )

                self.assertGreater(len(os.listdir(work_dir)), 0)


class StartAnalysisTask(TestCase):
    @given(text(), dictionaries(text(), text()))
    def test_lock_is_not_acquireable___retry_esception_is_raised(self, location, analysis_settings):
        with patch('fasteners.InterProcessLock.acquire', Mock(return_value=False)):
            with self.assertRaises(Retry):
                start_analysis_task(location, [analysis_settings])

    @given(text(), dictionaries(text(), text()))
    def test_lock_is_acquireable___start_analysis_is_ran(self, location, analysis_settings):
        with patch('src.model_execution_worker.tasks.start_analysis', Mock(return_value=True)) as start_analysis_mock:
            start_analysis_task.update_state = Mock()
            start_analysis_task(location, [analysis_settings])

            start_analysis_task.update_state.assert_called_once_with(state=status.STATUS_RUNNING)
            start_analysis_mock.assert_called_once_with(analysis_settings, location)
