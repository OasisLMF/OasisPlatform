from unittest.mock import MagicMock

from django.test import SimpleTestCase, override_settings

from src.server.oasisapi.files.models import file_storage_link

OBJECT_KEY = 'location/filename.csv'
PRESIGNED_URL = 'https://bucket.example.com/location/filename.csv?signature=xyz'


def fake_storage_obj():
    storage_obj = MagicMock()
    storage_obj.converted_file = None
    storage_obj.file.name = 'filename.csv'
    storage_obj.file.storage.location = 'location'
    storage_obj.file.storage.url.return_value = PRESIGNED_URL
    return storage_obj


class FileStorageLink(SimpleTestCase):

    @override_settings(STORAGE_TYPE='aws-s3', AWS_SHARED_BUCKET=False, AZURE_SHARED_CONTAINER=True)
    def test_s3_not_shared___presigned_url_returned(self):
        self.assertEqual(file_storage_link(fake_storage_obj()), PRESIGNED_URL)

    @override_settings(STORAGE_TYPE='aws-s3', AWS_SHARED_BUCKET=True, AZURE_SHARED_CONTAINER=False)
    def test_s3_shared___object_key_returned(self):
        self.assertEqual(file_storage_link(fake_storage_obj()), OBJECT_KEY)

    @override_settings(STORAGE_TYPE='aws-s3', AWS_SHARED_BUCKET=False)
    def test_s3_not_shared_fullpath___object_key_returned(self):
        self.assertEqual(file_storage_link(fake_storage_obj(), fullpath=True), OBJECT_KEY)

    @override_settings(STORAGE_TYPE='azure', AWS_SHARED_BUCKET=True, AZURE_SHARED_CONTAINER=False)
    def test_azure_not_shared___presigned_url_returned(self):
        self.assertEqual(file_storage_link(fake_storage_obj()), PRESIGNED_URL)

    @override_settings(STORAGE_TYPE='azure', AWS_SHARED_BUCKET=False, AZURE_SHARED_CONTAINER=True)
    def test_azure_shared___object_key_returned(self):
        self.assertEqual(file_storage_link(fake_storage_obj()), OBJECT_KEY)
