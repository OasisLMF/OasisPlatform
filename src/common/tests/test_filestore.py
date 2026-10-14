import os
from configparser import ConfigParser
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from oasis_data_manager.filestore.backends.azure_abfs import AzureABFSStorage

from src.common.filestore.azure import ContainerRootedAzureStorage
from src.common.filestore.filestore import get_filestore, remote_subdir


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
