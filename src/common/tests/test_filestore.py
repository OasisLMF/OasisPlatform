from types import SimpleNamespace
from unittest import TestCase

from src.common.filestore.filestore import remote_subdir


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
