import bz2
import gzip
import io
import lzma
import zipfile

import pandas as pd
from backports.tempfile import TemporaryDirectory
from django.test import TestCase, override_settings

from ...models import related_file_row_count, related_file_to_df
from .fakes import fake_related_file, FAKE_LOCATION_DATA


def zip_bytes(*names):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        for name in names:
            zf.writestr(name, FAKE_LOCATION_DATA)
    return buf.getvalue()


class RelatedFileRowCount(TestCase):
    def assert_row_count(self, related_file, expected):
        self.assertEqual(related_file_row_count(related_file), expected)
        # Should agree with loading the file into pandas
        self.assertEqual(len(related_file_to_df(related_file).index), expected)

    def test_no_file___returns_none(self):
        self.assertIsNone(related_file_row_count(None))

    def test_csv___header_is_not_counted(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                self.assert_row_count(fake_related_file(file=FAKE_LOCATION_DATA), 4)

    def test_csv_header_only___zero_rows(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                self.assert_row_count(fake_related_file(file='a,b,c\n'), 0)

    def test_csv_with_blank_lines_and_no_trailing_newline___matches_pandas(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                self.assert_row_count(fake_related_file(file='a,b\r\n1,2\r\n\r\n3,4\r\n\n5,6'), 3)

    def test_csv_with_quoted_newlines___matches_pandas(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                self.assert_row_count(fake_related_file(file='a,b\n1,"multi\nline"\n2,x\n'), 2)

    def test_parquet___count_read_from_metadata(self):
        buf = io.BytesIO()
        pd.read_csv(io.StringIO(FAKE_LOCATION_DATA)).to_parquet(buf)
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                related_file = fake_related_file(file=buf.getvalue(), content_type='application/octet-stream')
                self.assert_row_count(related_file, 4)

    def test_file_can_still_be_read_after_counting(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                related_file = fake_related_file(file=FAKE_LOCATION_DATA)
                related_file_row_count(related_file)
                self.assertEqual(related_file.read().decode(), FAKE_LOCATION_DATA)

    def test_compressed_csv___rows_are_counted(self):
        cases = [
            (gzip.compress(FAKE_LOCATION_DATA.encode()), 'application/gzip'),
            (bz2.compress(FAKE_LOCATION_DATA.encode()), 'application/x-bzip2'),
            (lzma.compress(FAKE_LOCATION_DATA.encode()), 'application/x-xz'),
            (zip_bytes('loc.csv'), 'application/zip'),
            # mimetypes infers 'loc.csv.gz' as text/csv, so compression is detected from the content
            (gzip.compress(FAKE_LOCATION_DATA.encode()), 'text/csv'),
        ]
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                for content, content_type in cases:
                    with self.subTest(content_type=content_type, magic=content[:2]):
                        related_file = fake_related_file(file=content, content_type=content_type)
                        self.assertEqual(related_file_row_count(related_file), 4)
                        self.assertEqual(related_file.read(), content)

    def test_zip_with_multiple_files___raises(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                related_file = fake_related_file(file=zip_bytes('a.csv', 'b.csv'), content_type='application/zip')
                with self.assertRaises(ValueError):
                    related_file_row_count(related_file)

    def test_parquet_with_wrong_content_type___count_read_from_metadata(self):
        buf = io.BytesIO()
        pd.read_csv(io.StringIO(FAKE_LOCATION_DATA)).to_parquet(buf)
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                related_file = fake_related_file(file=buf.getvalue(), content_type='text/csv')
                self.assertEqual(related_file_row_count(related_file), 4)
