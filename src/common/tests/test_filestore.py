from types import SimpleNamespace
from unittest import TestCase

from oasis_data_manager.filestore.backends.aws import AwsS3Storage

from src.common.filestore.filestore import strip_storage_location


class StripStorageLocation(TestCase):
    def setUp(self):
        self.filestore = AwsS3Storage(bucket_name='bucket', location='oasis/files')

    def test_key_with_location_prefix___prefix_is_removed(self):
        self.assertEqual(
            strip_storage_location(self.filestore, 'oasis/files/inputs.tar.gz'),
            'inputs.tar.gz',
        )

    def test_key_with_location_and_subdir___only_location_is_removed(self):
        self.assertEqual(
            strip_storage_location(self.filestore, 'oasis/files/analysis-1_files-abc/work-1.tar.gz'),
            'analysis-1_files-abc/work-1.tar.gz',
        )

    def test_key_without_location_prefix___is_unchanged(self):
        self.assertEqual(strip_storage_location(self.filestore, 'inputs.tar.gz'), 'inputs.tar.gz')

    def test_key_sharing_location_as_a_name_prefix___is_unchanged(self):
        self.assertEqual(
            strip_storage_location(self.filestore, 'oasis/files-old/inputs.tar.gz'),
            'oasis/files-old/inputs.tar.gz',
        )

    def test_location_with_surrounding_slashes___prefix_is_removed(self):
        filestore = AwsS3Storage(bucket_name='bucket', location='/oasis/files/')
        self.assertEqual(strip_storage_location(filestore, 'oasis/files/inputs.tar.gz'), 'inputs.tar.gz')

    def test_empty_location___key_is_unchanged(self):
        filestore = AwsS3Storage(bucket_name='bucket', location='')
        self.assertEqual(strip_storage_location(filestore, 'oasis/files/inputs.tar.gz'), 'oasis/files/inputs.tar.gz')

    def test_filestore_without_location_attribute___key_is_unchanged(self):
        self.assertEqual(strip_storage_location(SimpleNamespace(), 'inputs.tar.gz'), 'inputs.tar.gz')

    def test_none_reference___returns_none(self):
        self.assertIsNone(strip_storage_location(self.filestore, None))

    def test_storage_url_key_round_trips_to_the_name_it_was_built_from(self):
        key, _ = self.filestore.get_storage_url('location-converted.csv')
        self.assertEqual(key, 'oasis/files/location-converted.csv')
        self.assertEqual(strip_storage_location(self.filestore, key), 'location-converted.csv')
