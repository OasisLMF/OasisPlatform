from __future__ import absolute_import, unicode_literals

import string

import os
from backports.tempfile import TemporaryDirectory
from hypothesis import given
from hypothesis.strategies import binary, text, lists
from pathlib2 import Path

from src.conf.settings import SettingsPatcher
from .base import AppTestCase


class Outputs(AppTestCase):
    def test_file_does_not_exist___response_is_404(self):
        with TemporaryDirectory() as d:
            with SettingsPatcher(OUTPUTS_DATA_DIRECTORY=d):
                response = self.app.get('/outputs/somefile')

                self.assertEqual(response._status_code, 404)

    @given(text(min_size=1, max_size=10, alphabet=string.ascii_letters), binary(min_size=1, max_size=200))
    def test_file_exists___content_is_correct(self, location, data):
        with TemporaryDirectory() as d:
            with SettingsPatcher(OUTPUTS_DATA_DIRECTORY=d):
                with open(os.path.join(d, '{}.tar'.format(location)), 'wb') as f:
                    f.write(data)

                response = self.app.get('/outputs/{}'.format(location))

                self.assertEqual(response._status_code, 200)
                self.assertEqual(response.data, data)

    def test_no_location_is_given_on_delete___all_outputs_are_deleted(self):
        with TemporaryDirectory() as d:
            with SettingsPatcher(OUTPUTS_DATA_DIRECTORY=d):
                Path(os.path.join(d, 'test1.tar')).touch()
                Path(os.path.join(d, 'test2.tar')).touch()

                response = self.app.delete("/outputs")

                self.assertEqual(response._status_code, 200)
                self.assertEqual(len(os.listdir(d)), 0)

    def test_no_location_is_given_on_delete___non_tar_files_and_child_dirs_are_left(self):
        with TemporaryDirectory() as d:
            with SettingsPatcher(OUTPUTS_DATA_DIRECTORY=d):
                Path(os.path.join(d, 'test1.tar')).touch()
                Path(os.path.join(d, 'test2.tar')).touch()
                Path(os.path.join(d, 'test.nottar')).touch()
                os.makedirs(os.path.join(d, 'child.tar'))
                Path(os.path.join(d, 'child.tar', 'test3.tar')).touch()

                self.app.delete("/outputs")

                self.assertTrue(os.path.exists(os.path.join(d, 'test.nottar')))
                self.assertTrue(os.path.exists(os.path.join(d, 'child.tar', 'test3.tar')))

    @given(lists(text(alphabet=string.ascii_letters, min_size=1), unique=True, min_size=2, max_size=2))
    def test_location_is_given_on_delete___only_named_location_is_deleted(self, locations):
        first_location, second_location = locations

        with TemporaryDirectory() as d:
            with SettingsPatcher(OUTPUTS_DATA_DIRECTORY=d):
                Path(os.path.join(d, '{}.tar'.format(first_location))).touch()
                Path(os.path.join(d, '{}.tar'.format(second_location))).touch()

                response = self.app.delete("/outputs/{}".format(first_location))

                self.assertEqual(response._status_code, 200)
                self.assertEqual(os.listdir(d), ['{}.tar'.format(second_location)])

    @given(lists(text(alphabet=string.ascii_letters, min_size=1), unique=True, min_size=2, max_size=2))
    def test_location_does_not_exist___response_is_404(self, locations):
        first_location, second_location = locations

        with TemporaryDirectory() as d:
            with SettingsPatcher(OUTPUTS_DATA_DIRECTORY=d):
                Path(os.path.join(d, '{}.tar'.format(first_location))).touch()

                response = self.app.delete("/outputs/{}".format(second_location))

                self.assertEqual(response._status_code, 404)
                self.assertEqual(os.listdir(d), ['{}.tar'.format(first_location)])
