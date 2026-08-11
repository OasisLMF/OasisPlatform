from unittest import TestCase

import polars as pl
from backports.tempfile import TemporaryDirectory
from mock import patch
from pathlib2 import Path

from src.model_execution_worker.distributed_tasks import (
    merge_dataframes,
    _merge_csv_streaming,
    _merge_parquet_streaming,
    take_first,
)


def write_csv(path, rows):
    """rows: list of dicts with the same keys, written as a tiny CSV chunk file."""
    pl.DataFrame(rows).write_csv(str(path))


def write_parquet(path, rows):
    pl.DataFrame(rows).write_parquet(str(path))


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
