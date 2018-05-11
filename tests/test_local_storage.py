import string
from tempfile import NamedTemporaryFile
from unittest import TestCase

from backports.tempfile import TemporaryDirectory
from hypothesis import given
from hypothesis.strategies import binary, text
from pathlib2 import Path

from src.storage import LocalStorage


class LocalStorageSave(TestCase):
    @given(content=binary(min_size=1, max_size=10))
    def test_filename_is_not_provided___a_random_filename_is_generated(self, content):
        with TemporaryDirectory() as d:
            filename = LocalStorage(d).save(content)

            self.assertGreater(len(filename), 0)

            with open(str(Path(d, filename)), 'rb') as f:
                self.assertEqual(content, f.read())

    @given(
        content=binary(min_size=1, max_size=10),
        filename=text(alphabet=string.ascii_letters, min_size=1, max_size=10)
    )
    def test_filename_is_provided___content_is_stored_in_file(self, content, filename):
        with TemporaryDirectory() as d:
            LocalStorage(d).save(content, filename=filename)

            with open(str(Path(d, filename)), 'rb') as f:
                self.assertEqual(content, f.read())


class LocalStorageRead(TestCase):
    @given(content=binary(min_size=1, max_size=10))
    def test_filename_is_not_provided___a_random_filename_is_generated(self, content):
        with NamedTemporaryFile() as f:
            f.write(content)
            f.flush()

            read_content = LocalStorage(Path(f.name).parent).read(Path(f.name).name)

            self.assertEqual(content, read_content)
