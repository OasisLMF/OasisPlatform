import tarfile
from unittest import TestCase

import os
from backports.tempfile import TemporaryDirectory
from mock import patch
from pathlib2 import Path

from src.conf.settings import SettingsPatcher, settings
from src.model_execution_worker.tasks import start_analysis, InvalidInputsException, MissingInputsException, \
    MissingModelDataException


class StartAnalysis(TestCase):
    def create_tar(self, target):
        with TemporaryDirectory() as input_path, tarfile.open(target, 'w') as tar:
            paths = [
                Path(input_path, 'events.bin'),
                Path(input_path, 'returnperiods.bin'),
                Path(input_path, 'occurrence.bin'),
                Path(input_path, 'periods.bin'),
            ]

            for path in paths:
                path.touch()
                tar.add(str(path), path.name)

    def test_input_tar_file_does_not_exist___exception_is_raised(self):
        with TemporaryDirectory() as inputs_dir:
            with SettingsPatcher(INPUTS_DATA_DIRECTORY=inputs_dir):
                self.assertRaises(MissingInputsException, start_analysis, {}, 'non-existant-location')

    def test_input_location_is_not_a_tar___exception_is_raised(self):
        with TemporaryDirectory() as inputs_dir:
            with SettingsPatcher(INPUTS_DATA_DIRECTORY=inputs_dir):
                Path(inputs_dir, 'not-tar-file.tar').touch()

                self.assertRaises(InvalidInputsException, start_analysis, {}, 'not-tar-file')

    def test_input_model_data_does_not_exist___exception_is_raised(self):
        with TemporaryDirectory() as inputs_dir, TemporaryDirectory() as model_data_dir:
            with SettingsPatcher(INPUTS_DATA_DIRECTORY=inputs_dir, MODEL_DATA_DIRECTORY=model_data_dir):
                self.create_tar(str(Path(inputs_dir, 'location.tar')))

                self.assertRaises(
                    MissingModelDataException,
                    start_analysis,
                    {'analysis_settings': {
                        'source_tag': 'source',
                        'analysis_tag': 'source',
                        'module_supplier_id': 'supplier',
                        'model_version_id': 'version'
                    }},
                    'location',
                )

    def test_custom_model_runner_does_not_exist___default_runner_is_used(self):
        with TemporaryDirectory() as inputs_dir, \
                TemporaryDirectory() as model_data_dir, \
                TemporaryDirectory() as work_dir, \
                TemporaryDirectory() as out_dir:
            with SettingsPatcher(
                    INPUTS_DATA_DIRECTORY=inputs_dir,
                    MODEL_DATA_DIRECTORY=model_data_dir,
                    WORKING_DIRECTORY=work_dir,
                    OUTPUTS_DATA_DIRECTORY=out_dir):
                self.create_tar(str(Path(inputs_dir, 'location.tar')))
                Path(model_data_dir, 'supplier', 'version').mkdir(parents=True)

                with patch('src.model_execution_worker.tasks.supplier_model_runner') as default_mock:
                    start_analysis({
                        'analysis_settings': {
                            'source_tag': 'source',
                            'analysis_tag': 'source',
                            'module_supplier_id': 'supplier',
                            'model_version_id': 'version'
                        }},
                        'location',
                    )
                    default_mock.run.assert_called_once_with(
                        {
                            'source_tag': 'source',
                            'analysis_tag': 'source',
                            'module_supplier_id': 'supplier',
                            'model_version_id': 'version'
                        },
                        settings.get('worker', 'KTOOLS_BATCH_COUNT')
                    )

    def test_custom_model_runner_exists___custom_runner_is_used(self):
        with TemporaryDirectory() as inputs_dir, \
                TemporaryDirectory() as model_data_dir, \
                TemporaryDirectory() as work_dir, \
                TemporaryDirectory() as out_dir, \
                TemporaryDirectory() as module_dir:
            with SettingsPatcher(
                    INPUTS_DATA_DIRECTORY=inputs_dir,
                    MODEL_DATA_DIRECTORY=model_data_dir,
                    WORKING_DIRECTORY=work_dir,
                    OUTPUTS_DATA_DIRECTORY=out_dir,
                    SUPPLIER_MODULE_DIRECTORY=module_dir):
                self.create_tar(str(Path(inputs_dir, 'location.tar')))
                Path(model_data_dir, 'supplier', 'version').mkdir(parents=True)

                Path(module_dir, 'supplier').mkdir()
                Path(module_dir, 'supplier', '__init__.py').touch()
                with open(str(Path(module_dir, 'supplier').joinpath('supplier_model_runner.py')), 'w') as module:
                    module.writelines([
                        'from pathlib2 import Path\n',
                        'def run(settings, location):\n',
                        '    Path("{}", "custom_model").touch()\n'.format(out_dir)
                    ])

                start_analysis({
                    'analysis_settings': {
                        'source_tag': 'source',
                        'analysis_tag': 'source',
                        'module_supplier_id': 'supplier',
                        'model_version_id': 'version'
                    }},
                    'location',
                )
                self.assertTrue(Path(out_dir, "custom_model").exists())

    def test_do_clear_working_is_true___working_directory_is_removed_after_run(self):
        with TemporaryDirectory() as inputs_dir, \
                TemporaryDirectory() as model_data_dir, \
                TemporaryDirectory() as work_dir, \
                TemporaryDirectory() as out_dir:
            with SettingsPatcher(
                    INPUTS_DATA_DIRECTORY=inputs_dir,
                    MODEL_DATA_DIRECTORY=model_data_dir,
                    WORKING_DIRECTORY=work_dir,
                    OUTPUTS_DATA_DIRECTORY=out_dir,
                    DO_CLEAr_WORKING='True'):
                self.create_tar(str(Path(inputs_dir, 'location.tar')))
                Path(model_data_dir, 'supplier', 'version').mkdir(parents=True)

                with patch('src.model_execution_worker.tasks.supplier_model_runner'):
                    start_analysis({
                        'analysis_settings': {
                            'source_tag': 'source',
                            'analysis_tag': 'source',
                            'module_supplier_id': 'supplier',
                            'model_version_id': 'version'
                        }},
                        'location',
                    )

                self.assertEqual(0, len(os.listdir(work_dir)))

    def test_do_clear_working_is_false___working_directory_is_not_removed_after_run(self):
        with TemporaryDirectory() as inputs_dir, \
                TemporaryDirectory() as model_data_dir, \
                TemporaryDirectory() as work_dir, \
                TemporaryDirectory() as out_dir:
            with SettingsPatcher(
                    INPUTS_DATA_DIRECTORY=inputs_dir,
                    MODEL_DATA_DIRECTORY=model_data_dir,
                    WORKING_DIRECTORY=work_dir,
                    OUTPUTS_DATA_DIRECTORY=out_dir,
                    DO_CLEAr_WORKING='False'):
                self.create_tar(str(Path(inputs_dir, 'location.tar')))
                Path(model_data_dir, 'supplier', 'version').mkdir(parents=True)

                with patch('src.model_execution_worker.tasks.supplier_model_runner'):
                    start_analysis({
                        'analysis_settings': {
                            'source_tag': 'source',
                            'analysis_tag': 'source',
                            'module_supplier_id': 'supplier',
                            'model_version_id': 'version'
                        }},
                        'location',
                    )

                self.assertGreater(len(os.listdir(work_dir)), 0)
