import os
from unittest import TestCase

import pandas as pd
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
from backports.tempfile import TemporaryDirectory
from mock import patch
from oasislmf.computation.generate.files import GenerateFiles
from pathlib2 import Path

from src.model_execution_worker.distributed_tasks import (
    load_subject_at_risk_data,
    merge_dataframes,
    split_subject_at_risk_data,
    merge_chunk_log_storage,
    _merge_csv_streaming,
    _merge_parquet_streaming,
    take_first,
    handle_task_failure,
    generate_losses_output,
    prepare_losses_generation_directory,
    write_input_files,
    get_keys_format,
)


def write_csv(path, rows):
    """rows: list of dicts with the same keys, written as a tiny CSV chunk file."""
    pl.DataFrame(rows).write_csv(str(path))


def write_parquet(path, rows):
    pl.DataFrame(rows).write_parquet(str(path))


def write_zero_row_parquet(path, columns):
    """Zero-row chunk as oasislmf writes it: every column has the arrow null type."""
    pq.write_table(pa.Table.from_pandas(pd.DataFrame(columns=columns)), str(path))


class MergeCsvStreaming(TestCase):
    def test_disjoint_chunks_are_concatenated(self):
        with TemporaryDirectory() as tmp_dir:
            chunk_a = Path(tmp_dir, 'a.csv')
            chunk_b = Path(tmp_dir, 'b.csv')
            output_file = Path(tmp_dir, 'merged.csv')
            write_csv(chunk_a, [{'id': 1, 'value': 'x'}, {'id': 2, 'value': 'y'}])
            write_csv(chunk_b, [{'id': 3, 'value': 'z'}])

            _merge_csv_streaming([chunk_a, chunk_b], output_file)

            merged = pl.read_csv(str(output_file)).sort('id')
            self.assertEqual(merged['id'].to_list(), [1, 2, 3])

    def test_duplicate_rows_across_chunks_are_deduped(self):
        with TemporaryDirectory() as tmp_dir:
            chunk_a = Path(tmp_dir, 'a.csv')
            chunk_b = Path(tmp_dir, 'b.csv')
            output_file = Path(tmp_dir, 'merged.csv')
            write_csv(chunk_a, [{'id': 1, 'value': 'x'}])
            write_csv(chunk_b, [{'id': 1, 'value': 'x'}, {'id': 2, 'value': 'y'}])

            _merge_csv_streaming([chunk_a, chunk_b], output_file)

            merged = pl.read_csv(str(output_file))
            self.assertEqual(len(merged), 2)

    def test_differing_columns_are_diagonally_concatenated(self):
        with TemporaryDirectory() as tmp_dir:
            chunk_a = Path(tmp_dir, 'a.csv')
            chunk_b = Path(tmp_dir, 'b.csv')
            output_file = Path(tmp_dir, 'merged.csv')
            write_csv(chunk_a, [{'id': 1, 'value': 'x'}])
            write_csv(chunk_b, [{'id': 2, 'extra': 'only-in-b'}])

            _merge_csv_streaming([chunk_a, chunk_b], output_file)

            merged = pl.read_csv(str(output_file)).sort('id')
            self.assertEqual(set(merged.columns), {'id', 'value', 'extra'})
            self.assertIsNone(merged.filter(pl.col('id') == 1)['extra'][0])
            self.assertIsNone(merged.filter(pl.col('id') == 2)['value'][0])

    def test_empty_chunk_files_are_skipped(self):
        with TemporaryDirectory() as tmp_dir:
            chunk_a = Path(tmp_dir, 'a.csv')
            empty_chunk = Path(tmp_dir, 'empty.csv')
            output_file = Path(tmp_dir, 'merged.csv')
            write_csv(chunk_a, [{'id': 1, 'value': 'x'}])
            empty_chunk.touch()

            _merge_csv_streaming([chunk_a, empty_chunk], output_file)

            merged = pl.read_csv(str(output_file))
            self.assertEqual(merged['id'].to_list(), [1])

    def test_header_only_chunk_merges_with_typed_chunk_in_either_order(self):
        for header_first in (True, False):
            with self.subTest(header_first=header_first), TemporaryDirectory() as tmp_dir:
                header_only = Path(tmp_dir, 'header.csv')
                chunk_a = Path(tmp_dir, 'a.csv')
                output_file = Path(tmp_dir, 'merged.csv')
                header_only.write_text('id,value\n')
                write_csv(chunk_a, [{'id': 1, 'value': 'x'}])
                chunks = [header_only, chunk_a] if header_first else [chunk_a, header_only]

                _merge_csv_streaming(chunks, output_file)

                merged = pl.read_csv(str(output_file))
                self.assertEqual(merged['id'].to_list(), [1])
                self.assertEqual(merged['value'].to_list(), ['x'])

    def test_all_chunks_empty___no_output_file_is_written(self):
        with TemporaryDirectory() as tmp_dir:
            empty_chunk = Path(tmp_dir, 'empty.csv')
            output_file = Path(tmp_dir, 'merged.csv')
            empty_chunk.touch()

            _merge_csv_streaming([empty_chunk], output_file)

            self.assertFalse(output_file.exists())


class MergeParquetStreaming(TestCase):
    def test_disjoint_chunks_are_concatenated(self):
        with TemporaryDirectory() as tmp_dir:
            chunk_a = Path(tmp_dir, 'a.parquet')
            chunk_b = Path(tmp_dir, 'b.parquet')
            output_file = Path(tmp_dir, 'merged.parquet')
            write_parquet(chunk_a, [{'id': 1, 'value': 'x'}, {'id': 2, 'value': 'y'}])
            write_parquet(chunk_b, [{'id': 3, 'value': 'z'}])

            _merge_parquet_streaming([chunk_a, chunk_b], output_file)

            merged = pl.read_parquet(str(output_file)).sort('id')
            self.assertEqual(merged['id'].to_list(), [1, 2, 3])

    def test_duplicate_rows_across_chunks_are_deduped(self):
        with TemporaryDirectory() as tmp_dir:
            chunk_a = Path(tmp_dir, 'a.parquet')
            chunk_b = Path(tmp_dir, 'b.parquet')
            output_file = Path(tmp_dir, 'merged.parquet')
            write_parquet(chunk_a, [{'id': 1, 'value': 'x'}])
            write_parquet(chunk_b, [{'id': 1, 'value': 'x'}, {'id': 2, 'value': 'y'}])

            _merge_parquet_streaming([chunk_a, chunk_b], output_file)

            merged = pl.read_parquet(str(output_file))
            self.assertEqual(len(merged), 2)

    def test_zero_row_chunk_first_keeps_typed_schema(self):
        # e.g. lookup-1 had no lookup errors but a later chunk did
        with TemporaryDirectory() as tmp_dir:
            zero_row = Path(tmp_dir, 'a.parquet')
            chunk_b = Path(tmp_dir, 'b.parquet')
            output_file = Path(tmp_dir, 'merged.parquet')
            write_zero_row_parquet(zero_row, ['id', 'value'])
            write_parquet(chunk_b, [{'id': 1, 'value': 'x'}])

            _merge_parquet_streaming([zero_row, chunk_b], output_file)

            merged = pl.read_parquet(str(output_file))
            self.assertEqual(merged['id'].to_list(), [1])
            self.assertEqual(merged.schema, {'id': pl.Int64, 'value': pl.String})

    def test_corrupt_file_is_skipped_and_valid_content_survives(self):
        with TemporaryDirectory() as tmp_dir:
            chunk_a = Path(tmp_dir, 'a.parquet')
            corrupt_chunk = Path(tmp_dir, 'corrupt.parquet')
            output_file = Path(tmp_dir, 'merged.parquet')
            write_parquet(chunk_a, [{'id': 1, 'value': 'x'}])
            corrupt_chunk.write_bytes(b'not a real parquet file')

            _merge_parquet_streaming([chunk_a, corrupt_chunk], output_file)

            merged = pl.read_parquet(str(output_file))
            self.assertEqual(merged['id'].to_list(), [1])

    def test_all_chunks_invalid___no_output_file_is_written(self):
        with TemporaryDirectory() as tmp_dir:
            corrupt_chunk = Path(tmp_dir, 'corrupt.parquet')
            output_file = Path(tmp_dir, 'merged.parquet')
            corrupt_chunk.write_bytes(b'not a real parquet file')

            _merge_parquet_streaming([corrupt_chunk], output_file)

            self.assertFalse(output_file.exists())


class MergeDataframes(TestCase):
    def test_empty_path_list___warns_and_returns_without_dispatching(self):
        with patch('src.model_execution_worker.distributed_tasks._merge_csv_streaming') as csv_mock, \
                patch('src.model_execution_worker.distributed_tasks._merge_parquet_streaming') as parquet_mock, \
                patch('src.model_execution_worker.distributed_tasks.logger') as logger_mock:
            merge_dataframes([], 'output.csv', 'csv')

            csv_mock.assert_not_called()
            parquet_mock.assert_not_called()
            logger_mock.warning.assert_called_once()

    def test_csv_file_type___dispatches_to_csv_streaming(self):
        with patch('src.model_execution_worker.distributed_tasks._merge_csv_streaming') as csv_mock, \
                patch('src.model_execution_worker.distributed_tasks._merge_parquet_streaming') as parquet_mock:
            merge_dataframes(['a.csv'], 'output.csv', 'csv')

            csv_mock.assert_called_once_with(['a.csv'], 'output.csv')
            parquet_mock.assert_not_called()

    def test_parquet_file_type___dispatches_to_parquet_streaming(self):
        with patch('src.model_execution_worker.distributed_tasks._merge_csv_streaming') as csv_mock, \
                patch('src.model_execution_worker.distributed_tasks._merge_parquet_streaming') as parquet_mock:
            merge_dataframes(['a.parquet'], 'output.parquet', 'parquet')

            parquet_mock.assert_called_once_with(['a.parquet'], 'output.parquet')
            csv_mock.assert_not_called()


class TakeFirst(TestCase):
    def test_first_path_is_copied_to_output___others_are_ignored(self):
        with TemporaryDirectory() as tmp_dir:
            first = Path(tmp_dir, 'first.bin')
            second = Path(tmp_dir, 'second.bin')
            output_file = Path(tmp_dir, 'out.bin')
            first.write_bytes(b'first-content')
            second.write_bytes(b'second-content')

            take_first([first, second], output_file)

            self.assertEqual(output_file.read_bytes(), b'first-content')


class SplitSubjectAtRiskData(TestCase):
    def test_all_subjects_are_covered_once_across_chunks(self):
        sar_df = pd.DataFrame({'loc_id': range(1, 11), 'value': range(10)})

        chunks = [split_subject_at_risk_data(sar_df, 3, idx) for idx in range(3)]

        self.assertEqual(sorted(pd.concat(chunks)['loc_id'].to_list()), list(range(1, 11)))
        for chunk in chunks:
            self.assertEqual(chunk.index.to_list(), list(range(len(chunk))))

    def test_rows_sharing_a_subject_id_stay_in_the_same_chunk(self):
        # e.g. an account only (cyber) portfolio, with several layers per account
        sar_df = pd.DataFrame({'loc_id': [1, 1, 2, 2, 2, 3], 'LayerNumber': [1, 2, 1, 2, 3, 1]})

        chunks = [split_subject_at_risk_data(sar_df, 2, idx) for idx in range(2)]

        self.assertEqual(chunks[0]['loc_id'].to_list(), [1, 1, 2, 2, 2])
        self.assertEqual(chunks[1]['loc_id'].to_list(), [3])

    def test_more_chunks_than_subjects___extra_chunks_are_empty(self):
        sar_df = pd.DataFrame({'loc_id': [1, 2]})

        chunks = [split_subject_at_risk_data(sar_df, 4, idx) for idx in range(4)]

        self.assertEqual([len(c) for c in chunks], [1, 1, 0, 0])


class LoadSubjectAtRiskData(TestCase):
    inputs_dir = os.path.join(os.path.dirname(__file__), 'inputs')

    def test_property_portfolio___location_rows_are_returned(self):
        params = {
            'oed_location_csv': os.path.join(self.inputs_dir, 'location.csv'),
            'oed_accounts_csv': os.path.join(self.inputs_dir, 'accounts.csv'),
        }
        expected_rows = len(pd.read_csv(params['oed_location_csv']))

        sar_df = load_subject_at_risk_data(params)

        self.assertEqual(len(sar_df), expected_rows)
        self.assertIn('loc_id', sar_df.columns)
        self.assertIn('LocNumber', sar_df.columns)


class MergeChunkLogStorage(TestCase):
    """ Regression tests for 'collect_keys': it used to build its return value from
        only 'params[0]' (the first lookup chunk's result), which silently dropped
        every other chunk's own step log from 'log_storage'. 'merge_chunk_log_storage'
        is the extracted fix - it must combine every chunk's entries.
    """

    def test_each_chunks_own_log_entry_is_kept(self):
        chunk_results = [
            {'log_storage': {'prepare-keys-file-chunk-0': 'loc-0'}},
            {'log_storage': {'prepare-keys-file-chunk-1': 'loc-1'}},
            {'log_storage': {'prepare-keys-file-chunk-2': 'loc-2'}},
        ]

        merged = merge_chunk_log_storage(chunk_results)

        self.assertEqual(merged, {
            'prepare-keys-file-chunk-0': 'loc-0',
            'prepare-keys-file-chunk-1': 'loc-1',
            'prepare-keys-file-chunk-2': 'loc-2',
        })

    def test_shared_earlier_step_entries_are_not_duplicated(self):
        # every chunk also carries forward the log_storage from steps before the
        # chord (e.g. 'pre-analysis-hook'), which is identical across all chunks
        chunk_results = [
            {'log_storage': {'pre-analysis-hook': 'loc-hook', 'prepare-keys-file-chunk-0': 'loc-0'}},
            {'log_storage': {'pre-analysis-hook': 'loc-hook', 'prepare-keys-file-chunk-1': 'loc-1'}},
        ]

        merged = merge_chunk_log_storage(chunk_results)

        self.assertEqual(merged, {
            'pre-analysis-hook': 'loc-hook',
            'prepare-keys-file-chunk-0': 'loc-0',
            'prepare-keys-file-chunk-1': 'loc-1',
        })

    def test_missing_log_storage_key_is_tolerated(self):
        chunk_results = [{'log_storage': {'prepare-keys-file-chunk-0': 'loc-0'}}, {}]

        merged = merge_chunk_log_storage(chunk_results)

        self.assertEqual(merged, {'prepare-keys-file-chunk-0': 'loc-0'})

    def test_no_chunks___returns_empty_dict(self):
        self.assertEqual(merge_chunk_log_storage([]), {})


class HandleTaskFailureSignal(TestCase):
    """ Tests for the worker-side 'task_failure' signal handler that uploads a failed
        task's local log file (which includes any KERNEL_STDERR/STDOUT output logged
        before the failure) to the filestore.
    """

    def _task_args(self, **overrides):
        return {
            'analysis_id': 1,
            'initiator_id': 2,
            'slug': 'generate-losses-chunk-1',
            'run_data_uuid': 'run-uuid',
            **overrides,
        }

    def test_log_file_present___is_uploaded_dispatched_and_removed_locally(self):
        with TemporaryDirectory() as tmp_dir:
            task_args = self._task_args()
            log_path = os.path.join(tmp_dir, f"{task_args['run_data_uuid']}_{task_args['slug']}.log")
            with open(log_path, 'w') as f:
                f.write('KERNEL_STDERR:\nboom\nSTDOUT:\nfailure output\n')

            with patch('src.model_execution_worker.distributed_tasks.TASK_LOG_DIR', tmp_dir), \
                    patch('src.model_execution_worker.distributed_tasks.filestore') as filestore_mock, \
                    patch('src.model_execution_worker.distributed_tasks.signature') as signature_mock:
                filestore_mock.put.return_value = 'remote/log-location.txt'

                handle_task_failure(kwargs=task_args, args=[], task_id='task-99')

                filestore_mock.put.assert_any_call(log_path)
                signature_mock.assert_any_call('subtask_error_log')
                signature_mock.return_value.delay.assert_any_call(
                    task_args['analysis_id'],
                    task_args['initiator_id'],
                    task_args['slug'],
                    'task-99',
                    'remote/log-location.txt',
                )

            # local copy is removed once it has been uploaded
            self.assertFalse(os.path.isfile(log_path))

    def test_log_file_missing___no_upload_is_attempted_and_no_error_is_raised(self):
        with TemporaryDirectory() as tmp_dir:
            task_args = self._task_args(slug='some-other-task')

            with patch('src.model_execution_worker.distributed_tasks.TASK_LOG_DIR', tmp_dir), \
                    patch('src.model_execution_worker.distributed_tasks.filestore') as filestore_mock, \
                    patch('src.model_execution_worker.distributed_tasks.signature') as signature_mock:
                handle_task_failure(kwargs=task_args, args=[], task_id='task-1')

                filestore_mock.put.assert_not_called()
                dispatched_names = [c.args[0] for c in signature_mock.call_args_list]
                self.assertNotIn('subtask_error_log', dispatched_names)


class GenerateLossesOutputCombineFiles(TestCase):
    """ occurrence.bin is produced during the loss run but is needed later by the combine endpoint.
        It is shipped inside the output tarball (output/combine/occurrence.bin) so the inputs
        tarball never has to be re-uploaded.
    """

    def _run_generate_losses_output(self, run_dir, occurrence_in_run_dir=True, **chunk_params):
        root_dir = Path(run_dir, 'analysis-1_losses-run-uuid')
        oasis_files_dir = Path(root_dir, 'input-data')
        model_run_dir = Path(root_dir, 'run-data')
        oasis_files_dir.mkdir(parents=True)
        Path(model_run_dir, 'input').mkdir(parents=True)
        if occurrence_in_run_dir:
            Path(model_run_dir, 'input', 'occurrence.bin').write_bytes(b'occurrence-data')

        def settings_get(section, option, fallback=None):
            return run_dir if option == 'base_run_dir' else fallback

        params = [{
            'chunk_work_location': 'work-1.tar.gz',
            'chunk_log_location': 'log-1.tar.gz',
            'input_location': 'stored-inputs.tar.gz',
            **chunk_params,
        }]
        with patch('src.model_execution_worker.distributed_tasks.TASK_LOG_DIR', run_dir), \
                patch('src.model_execution_worker.distributed_tasks.settings.get', side_effect=settings_get), \
                patch('src.model_execution_worker.distributed_tasks.notify_api_task_started'), \
                patch('src.model_execution_worker.distributed_tasks.filestore') as filestore_mock, \
                patch('oasislmf.manager.OasisManager'):
            filestore_mock.put.side_effect = lambda ref, filename=None, **kw: filename or f'{os.path.basename(str(ref))}.tar.gz'
            result = generate_losses_output.run(params, analysis_id=1, run_data_uuid='run-uuid', slug='generate-losses-output')

        return result, filestore_mock, oasis_files_dir, model_run_dir

    def test_occurrence_file_exists___copied_to_output_combine_dir(self):
        with TemporaryDirectory() as run_dir:
            _, filestore_mock, _, model_run_dir = self._run_generate_losses_output(run_dir)

            combine_occ = Path(model_run_dir, 'output', 'combine', 'occurrence.bin')
            self.assertTrue(combine_occ.is_file())
            self.assertEqual(combine_occ.read_bytes(), b'occurrence-data')
            filestore_mock.put.assert_any_call(str(Path(model_run_dir, 'output')), arcname='output')

    def test_occurrence_file_exists___inputs_are_not_reuploaded(self):
        with TemporaryDirectory() as run_dir:
            result, filestore_mock, oasis_files_dir, _ = self._run_generate_losses_output(run_dir)

            input_puts = [c for c in filestore_mock.put.call_args_list if c.args[0] == str(oasis_files_dir)]
            self.assertEqual(input_puts, [])

    def test_generate_and_run___inputs_are_not_reuploaded(self):
        with TemporaryDirectory() as run_dir:
            result, filestore_mock, oasis_files_dir, _ = self._run_generate_losses_output(
                run_dir, **{'input-location_generate-and-run': 'oasis/worker/worker-inputs.tar.gz'})

            input_puts = [c for c in filestore_mock.put.call_args_list if c.args[0] == str(oasis_files_dir)]
            self.assertEqual(input_puts, [])

    def test_occurrence_file_missing___no_combine_dir_and_no_error(self):
        with TemporaryDirectory() as run_dir:
            result, _, _, model_run_dir = self._run_generate_losses_output(run_dir, occurrence_in_run_dir=False)

            self.assertFalse(Path(model_run_dir, 'output', 'combine').exists())
            self.assertIn('output_location', result)


class WriteInputFiles(TestCase):
    """ The collected keys must reach oasislmf under the parameter names it reads,
        otherwise 'GenerateFiles' silently re-runs the full keys lookup on the
        whole portfolio in a single task.
    """

    def _run_write_input_files(self, run_dir, keys_format=None):
        def extract_keys(archive, target_dir, subdir):
            Path(target_dir).mkdir(parents=True, exist_ok=True)
            keys = pl.DataFrame(schema=['LocID', 'PerilID', 'CoverageTypeID', 'AreaPerilID', 'VulnerabilityID'])
            errors = pl.DataFrame(schema=['LocID', 'PerilID', 'CoverageTypeID', 'Status', 'Message'])
            if keys_format == 'oasis':
                keys.write_csv(str(Path(target_dir, 'keys.csv')))
                errors.write_csv(str(Path(target_dir, 'keys-errors.csv')))
            else:
                keys.write_parquet(str(Path(target_dir, 'keys.parquet')))
                errors.write_parquet(str(Path(target_dir, 'keys-errors.parquet')))

        def settings_get(section, option, fallback=None):
            return run_dir if option == 'base_run_dir' else fallback

        params = {'keys_data': 'keys-data.tar.gz', 'log_storage': {}}
        if keys_format:
            params['keys_format'] = keys_format
        with patch('src.model_execution_worker.distributed_tasks.TASK_LOG_DIR', run_dir), \
                patch('src.model_execution_worker.distributed_tasks.settings.get', side_effect=settings_get), \
                patch('src.model_execution_worker.distributed_tasks.notify_api_task_started'), \
                patch('src.model_execution_worker.distributed_tasks.filestore') as filestore_mock, \
                patch('oasislmf.manager.OasisManager') as manager_mock:
            filestore_mock.extract.side_effect = extract_keys
            write_input_files.run(params, analysis_id=1, run_data_uuid='run-uuid', slug='write-input-files')

        manager_mock.return_value.generate_files.assert_called_once()
        return manager_mock.return_value.generate_files.call_args.kwargs

    def test_collected_keys_are_passed_to_generate_files(self):
        with TemporaryDirectory() as run_dir:
            generate_kwargs = self._run_write_input_files(run_dir)

            target_dir = generate_kwargs['target_dir']
            self.assertEqual(generate_kwargs['keys_data_path'], os.path.join(target_dir, 'keys.parquet'))
            self.assertEqual(generate_kwargs['keys_errors_path'], os.path.join(target_dir, 'keys-errors.parquet'))

    def test_oasis_keys_format___csv_keys_are_passed_to_generate_files(self):
        with TemporaryDirectory() as run_dir:
            generate_kwargs = self._run_write_input_files(run_dir, keys_format='oasis')

            target_dir = generate_kwargs['target_dir']
            self.assertEqual(generate_kwargs['keys_data_path'], os.path.join(target_dir, 'keys.csv'))
            self.assertEqual(generate_kwargs['keys_errors_path'], os.path.join(target_dir, 'keys-errors.csv'))

    def test_generate_files_receives_pre_generated_keys___lookup_is_skipped(self):
        # Build the real oasislmf step from the kwargs the worker passes, so a future
        # rename of the keys parameters in oasislmf also fails this test
        with TemporaryDirectory() as run_dir:
            generate_kwargs = self._run_write_input_files(run_dir)
            generate_files = GenerateFiles(**generate_kwargs)

            target_dir = generate_kwargs['target_dir']
            self.assertEqual(generate_files.keys_data_path, os.path.join(target_dir, 'keys.parquet'))
            self.assertEqual(generate_files.keys_errors_path, os.path.join(target_dir, 'keys-errors.parquet'))


class GetKeysFormat(TestCase):
    def test_missing_keys_format___defaults_to_parquet(self):
        self.assertEqual(get_keys_format({}), ('parquet', 'parquet'))

    def test_oasis_keys_format___uses_csv(self):
        self.assertEqual(get_keys_format({'keys_format': 'oasis'}), ('oasis', 'csv'))

    def test_keys_format_is_case_insensitive(self):
        self.assertEqual(get_keys_format({'keys_format': 'Parquet'}), ('parquet', 'parquet'))

    def test_json_keys_format___falls_back_to_parquet(self):
        # chunk merging only handles tabular formats
        self.assertEqual(get_keys_format({'keys_format': 'json'}), ('parquet', 'parquet'))


class ArchiveCompressionType(TestCase):
    """ Every directory archive the worker stores follows ARCHIVE_COMPRESSION_TYPE """

    def test_zst___run_directory_is_stored_as_zstd(self):
        def settings_get(section, option, fallback=None):
            return run_dir if option == 'base_run_dir' else fallback

        with TemporaryDirectory() as run_dir, \
                patch('src.model_execution_worker.distributed_tasks.TASK_LOG_DIR', run_dir), \
                patch('src.model_execution_worker.distributed_tasks.ARCHIVE_COMPRESSION_TYPE', 'zst'), \
                patch('src.model_execution_worker.distributed_tasks.settings.get', side_effect=settings_get), \
                patch('src.model_execution_worker.distributed_tasks.notify_api_task_started'), \
                patch('src.model_execution_worker.distributed_tasks.filestore') as filestore_mock, \
                patch('oasislmf.manager.OasisManager'):
            filestore_mock.archive_suffix.side_effect = lambda compression: {'gz': 'tar.gz', 'zst': 'tar.zst'}[compression]
            prepare_losses_generation_directory.run(
                {}, analysis_id=1, run_data_uuid='run-uuid', slug='prepare-losses-generation-directory')

        run_dir_puts = [c for c in filestore_mock.put.call_args_list if c.kwargs.get('filename', '').startswith('run_directory')]
        self.assertEqual(len(run_dir_puts), 1)
        self.assertEqual(run_dir_puts[0].kwargs['filename'], 'run_directory.tar.zst')
        self.assertEqual(run_dir_puts[0].kwargs['compression'], 'zst')

    def test_zst___outputs_and_logs_are_stored_as_zstd(self):
        with TemporaryDirectory() as run_dir:
            root_dir = Path(run_dir, 'analysis-1_losses-run-uuid')
            model_run_dir = Path(root_dir, 'run-data')
            Path(root_dir, 'input-data').mkdir(parents=True)
            Path(model_run_dir, 'input').mkdir(parents=True)
            Path(model_run_dir, 'input', 'occurrence.bin').write_bytes(b'')

            def settings_get(section, option, fallback=None):
                return run_dir if option == 'base_run_dir' else fallback

            with patch('src.model_execution_worker.distributed_tasks.TASK_LOG_DIR', run_dir), \
                    patch('src.model_execution_worker.distributed_tasks.ARCHIVE_COMPRESSION_TYPE', 'zst'), \
                    patch('src.model_execution_worker.distributed_tasks.settings.get', side_effect=settings_get), \
                    patch('src.model_execution_worker.distributed_tasks.notify_api_task_started'), \
                    patch('src.model_execution_worker.distributed_tasks.filestore') as filestore_mock, \
                    patch('oasislmf.manager.OasisManager'):
                filestore_mock.put.side_effect = lambda ref, filename=None, **kw: filename or 'stored.tar.zst'
                params = [{'chunk_work_location': 'work-1.tar.zst', 'chunk_log_location': 'log-1.tar.zst',
                           'input_location': 'stored-inputs.tar.zst'}]
                generate_losses_output.run(params, analysis_id=1, run_data_uuid='run-uuid', slug='generate-losses-output')

            dir_puts = {c.args[0]: c.kwargs.get('compression') for c in filestore_mock.put.call_args_list}
            for name in ['output', 'log']:
                self.assertEqual(dir_puts[str(Path(model_run_dir, name))], 'zst')
            self.assertEqual(dir_puts[str(Path(root_dir, 'input-data'))], 'zst')
