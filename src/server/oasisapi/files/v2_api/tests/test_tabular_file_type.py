from unittest import TestCase

from src.server.oasisapi.files.models import tabular_file_type


class TabularFileType(TestCase):
    def test_parquet_references___parquet_type(self):
        for ref in [
            '/shared-fs/0a1b2c3d.parquet',
            'https://bucket.s3.amazonaws.com/0a1b2c3d.parquet?X-Amz-Signature=abc',
            '0a1b2c3d.parquet_abc4def',
        ]:
            self.assertEqual(tabular_file_type(ref), ('application/octet-stream', 'parquet'), ref)

    def test_csv_references___csv_type(self):
        for ref in [
            '/shared-fs/0a1b2c3d.csv',
            'https://bucket.s3.amazonaws.com/0a1b2c3d.csv?X-Amz-Signature=abc',
            'no_extension',
            None,
        ]:
            self.assertEqual(tabular_file_type(ref), ('text/csv', 'csv'), ref)
