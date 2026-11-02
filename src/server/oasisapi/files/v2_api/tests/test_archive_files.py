import os
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from oasis_data_manager.filestore.archive import compress_dir
from pathlib2 import Path

from ...models import archive_suffix, extract_file_from_tar, list_tar_file
from ....analyses.v2_api.utils import store_archive


def stored_archive(compression):
    """ A stored worker archive holding 'output/0_alt.csv' """
    with TemporaryDirectory() as d:
        Path(d, 'output').mkdir()
        Path(d, 'output', '0_alt.csv').write_text('a,b\n1,2\n')
        archive_fp = os.path.join(d, 'archive')
        compress_dir(archive_fp, os.path.join(d, 'output'), arcname='output', compression=compression)
        data = Path(archive_fp).read_bytes()
    return SimpleNamespace(read=lambda: data)


class TarFiles(TestCase):
    """ The tar list/extract endpoints read gzip and zstd worker archives """

    def test_gzip___members_are_listed_and_extracted(self):
        self.assertIn('output/0_alt.csv', list_tar_file(stored_archive('gz')))
        self.assertEqual(extract_file_from_tar(stored_archive('gz'), 'output/0_alt.csv').read(), b'a,b\n1,2\n')

    def test_zstd___members_are_listed_and_extracted(self):
        self.assertIn('output/0_alt.csv', list_tar_file(stored_archive('zst')))
        self.assertEqual(extract_file_from_tar(stored_archive('zst'), 'output/0_alt.csv').read(), b'a,b\n1,2\n')


class StoreArchive(TestCase):
    """ Worker archives are stored with the suffix and content type of their compression """

    def test_archive_suffix___from_key_path_or_url(self):
        self.assertEqual(archive_suffix('analysis-1/abc.tar.zst'), 'tar.zst')
        self.assertEqual(archive_suffix('https://bucket.s3.amazonaws.com/oasis/abc.tar.zst?X-Amz-Signature=abc'), 'tar.zst')
        self.assertEqual(archive_suffix('abc.tar.gz'), 'tar.gz')
        self.assertEqual(archive_suffix('abc'), 'tar.gz')

    def test_zstd_reference___stored_as_tar_zst(self):
        with patch('src.server.oasisapi.analyses.v2_api.utils.store_file') as store_file_mock:
            store_archive('analysis-1/abc.tar.zst', 'user', 'analysis_1_output')

        store_file_mock.assert_called_once_with('analysis-1/abc.tar.zst', 'application/zstd', 'user',
                                                required=True, filename='analysis_1_output.tar.zst')

    def test_gzip_reference___stored_as_tar_gz(self):
        with patch('src.server.oasisapi.analyses.v2_api.utils.store_file') as store_file_mock:
            store_archive('analysis-1/abc.tar.gz', 'user', 'analysis_1_output')

        store_file_mock.assert_called_once_with('analysis-1/abc.tar.gz', 'application/gzip', 'user',
                                                required=True, filename='analysis_1_output.tar.gz')
