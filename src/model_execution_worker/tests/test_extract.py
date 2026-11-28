"""Shared run data is extracted once, and a failed extraction is never reused (OasisPlatform#1500)."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from src.model_execution_worker.extract import extract_tar_once


class FakeFilestore:
    """Writes some files into target_dir, then optionally fails part way."""

    def __init__(self, fail=False):
        self.fail = fail
        self.calls = 0

    def extract(self, reference, target_dir, storage_subdir=''):
        self.calls += 1
        Path(target_dir, 'static').mkdir(parents=True)
        Path(target_dir, 'static', 'first.bin').write_text(reference)
        if self.fail:
            raise RuntimeError('extraction failed part way')
        Path(target_dir, 'static', 'footprint.bin').write_text(reference)


class ExtractTarOnce(TestCase):
    def test_extracts_into_dst(self):
        with TemporaryDirectory() as d:
            dst = os.path.join(d, 'run-data')
            extract_tar_once(FakeFilestore(), 'ref', dst)
            self.assertEqual(sorted(p.name for p in Path(dst, 'static').iterdir()), ['first.bin', 'footprint.bin'])
            self.assertFalse(Path(f'{dst}.partial').exists())

    def test_failed_extraction_leaves_no_dst_and_retry_extracts_again(self):
        with TemporaryDirectory() as d:
            dst = os.path.join(d, 'run-data')
            with self.assertRaises(RuntimeError):
                extract_tar_once(FakeFilestore(fail=True), 'ref', dst)
            self.assertFalse(Path(dst).exists())
            self.assertFalse(Path(f'{dst}.partial').exists())

            retry = FakeFilestore()
            extract_tar_once(retry, 'ref', dst)
            self.assertEqual(retry.calls, 1)
            self.assertTrue(Path(dst, 'static', 'footprint.bin').exists())

    def test_completed_extraction_is_not_repeated(self):
        with TemporaryDirectory() as d:
            dst = os.path.join(d, 'run-data')
            first, second = FakeFilestore(), FakeFilestore()
            extract_tar_once(first, 'ref', dst)
            extract_tar_once(second, 'ref', dst)
            self.assertEqual((first.calls, second.calls), (1, 0))

    def test_leftover_partial_from_a_killed_worker_is_replaced(self):
        with TemporaryDirectory() as d:
            dst = os.path.join(d, 'run-data')
            Path(f'{dst}.partial', 'static').mkdir(parents=True)
            Path(f'{dst}.partial', 'static', 'stale.bin').write_text('stale')
            extract_tar_once(FakeFilestore(), 'ref', dst)
            self.assertFalse(Path(dst, 'static', 'stale.bin').exists())
            self.assertTrue(Path(dst, 'static', 'footprint.bin').exists())
