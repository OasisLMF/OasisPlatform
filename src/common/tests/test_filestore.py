import os
from configparser import ConfigParser
from contextlib import nullcontext
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from oasis_data_manager.filestore.backends.azure_abfs import AzureABFSStorage

from src.common.filestore.azure import ContainerRootedAzureStorage
from src.common.filestore.filestore import get_archive_compression, get_filestore, remote_subdir


class RemoteSubdir(TestCase):
    """ AwsS3Storage.put() prefixes `location` onto keys, so remote cleanup must delete
        under the same prefix or KEEP_REMOTE_DATA=False silently leaves run data behind.
    """

    def test_location_set___subdir_is_prefixed(self):
        filestore = SimpleNamespace(location='oasis/worker')
        self.assertEqual(remote_subdir(filestore, 'analysis-1_losses-uuid'), 'oasis/worker/analysis-1_losses-uuid')

    def test_location_empty___subdir_unchanged(self):
        filestore = SimpleNamespace(location='')
        self.assertEqual(remote_subdir(filestore, 'analysis-1_losses-uuid'), 'analysis-1_losses-uuid')

    def test_backend_without_location___subdir_unchanged(self):
        self.assertEqual(remote_subdir(SimpleNamespace(), 'analysis-1_losses-uuid'), 'analysis-1_losses-uuid')

    def test_no_subdir___returned_as_is(self):
        filestore = SimpleNamespace(location='oasis/worker')
        self.assertIsNone(remote_subdir(filestore, None))
        self.assertEqual(remote_subdir(filestore, ''), '')


class AzureWorkerFilestore(TestCase):
    """ The server exchanges container-relative blob names, so the worker's Azure store must be
        rooted at the container and put AZURE_LOCATION into the keys it returns.
    """

    def _settings(self, section='worker', **options):
        config = ConfigParser()
        config[section] = {
            'STORAGE_TYPE': 'azure',
            'AZURE_ACCOUNT_NAME': 'account',
            'AZURE_ACCOUNT_KEY': 'key',
            'AZURE_CONTAINER': 'container',
            'AZURE_LOCATION': 'oasis/worker',
            **options,
        }
        return config

    def test_worker_section___rooted_at_container_with_location_kept(self):
        filestore = get_filestore(self._settings())

        self.assertIsInstance(filestore, ContainerRootedAzureStorage)
        self.assertEqual(filestore.root_dir, 'container')
        self.assertEqual(filestore.location, 'oasis/worker')

    def test_put___location_is_prefixed_onto_returned_key(self):
        filestore = get_filestore(self._settings())
        with patch.object(AzureABFSStorage, 'put', side_effect=lambda ref, filename=None, subdir='', **kw: os.path.join(subdir, 'f.tar.gz')):
            self.assertEqual(filestore.put('/tmp/x'), 'oasis/worker/f.tar.gz')
            self.assertEqual(filestore.put('/tmp/x', subdir='analysis-1'), 'oasis/worker/analysis-1/f.tar.gz')

    def test_cleanup_subdir___matches_put_prefix(self):
        filestore = get_filestore(self._settings())
        self.assertEqual(remote_subdir(filestore, 'analysis-1'), 'oasis/worker/analysis-1')

    def test_model_data_section___location_stays_the_root(self):
        filestore = get_filestore(self._settings(section='worker.model_data'), section='worker.model_data')

        self.assertNotIsInstance(filestore, ContainerRootedAzureStorage)
        self.assertEqual(filestore.root_dir, 'container/oasis/worker')

    def test_root_dir_set___unchanged_behaviour(self):
        filestore = get_filestore(self._settings(ROOT_DIR='custom'))

        self.assertNotIsInstance(filestore, ContainerRootedAzureStorage)
        self.assertEqual(filestore.root_dir, 'container/custom')

    def test_boolean_options_set_false___parsed_as_false(self):
        filestore = get_filestore(self._settings(AZURE_SSL='False', AZURE_OVERWRITE_FILES='False', AZURE_SHARED_CONTAINER='False'))

        self.assertIs(filestore.azure_ssl, False)
        self.assertIs(filestore.overwrite_files, False)
        self.assertIs(filestore.shared_container, False)
        self.assertEqual(filestore.azure_protocol, 'http')

    def test_azure_log_level___read_from_azure_option(self):
        with patch.object(AzureABFSStorage, '__init__', return_value=None) as init:
            get_filestore(self._settings(AZURE_LOG_LEVEL='DEBUG', AWS_LOG_LEVEL='WARNING'))
            self.assertEqual(init.call_args.kwargs['azure_log_level'], 'DEBUG')

    def test_azure_log_level_unset___falls_back_to_aws_option(self):
        with patch.object(AzureABFSStorage, '__init__', return_value=None) as init:
            get_filestore(self._settings(AWS_LOG_LEVEL='WARNING'))
            self.assertEqual(init.call_args.kwargs['azure_log_level'], 'WARNING')


class ArchiveOptions(TestCase):
    """ Directory archives default to fast gzip; level and zstd threads are tunable per deployment """

    def _settings(self, **options):
        config = ConfigParser()
        config['worker'] = {'STORAGE_TYPE': 'local-fs', 'MEDIA_ROOT': '/tmp', **options}
        return config

    def test_no_archive_settings___format_defaults_are_used(self):
        filestore = get_filestore(self._settings())

        self.assertEqual(filestore.archive_compression, 'gz')
        self.assertIsNone(filestore.archive_compresslevel)
        self.assertEqual(filestore.archive_threads, -1)

    def test_archive_settings___passed_to_filestore(self):
        filestore = get_filestore(self._settings(ARCHIVE_COMPRESSION_LEVEL='6', ARCHIVE_COMPRESSION_THREADS='4'))

        self.assertEqual(filestore.archive_compresslevel, 6)
        self.assertEqual(filestore.archive_threads, 4)


class ArchiveCompressionType(TestCase):
    """ ARCHIVE_COMPRESSION_TYPE is passed to each directory `put`, never set as the filestore default """

    def _settings(self, **options):
        config = ConfigParser()
        config['worker'] = {'STORAGE_TYPE': 'local-fs', 'MEDIA_ROOT': '/tmp', **options}
        return config

    def test_not_set___gzip(self):
        self.assertEqual(get_archive_compression(self._settings()), 'gz')

    def test_zst___read_case_insensitively(self):
        self.assertEqual(get_archive_compression(self._settings(ARCHIVE_COMPRESSION_TYPE='ZST')), 'zst')

    def test_zst___surrounding_whitespace_is_ignored(self):
        self.assertEqual(get_archive_compression(self._settings(ARCHIVE_COMPRESSION_TYPE=' zst ')), 'zst')

    def test_unknown_value___falls_back_to_gzip(self):
        for value in ['zstd', 'gzip', 'tar.zst', 'none', '']:
            with self.subTest(value=value), self.assertLogs(level='WARNING') if value else nullcontext():
                self.assertEqual(get_archive_compression(self._settings(ARCHIVE_COMPRESSION_TYPE=value)), 'gz')

    def test_zst___filestore_default_stays_gzip(self):
        filestore = get_filestore(self._settings(ARCHIVE_COMPRESSION_TYPE='zst'))

        self.assertEqual(filestore.archive_compression, 'gz')
