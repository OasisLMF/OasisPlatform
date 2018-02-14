# -*- coding: utf-8 -*-
from __future__ import absolute_import

import io
import os
import string

from backports.tempfile import TemporaryDirectory
from flask import json
from hypothesis import given
from hypothesis.strategies import text, integers, binary, lists
from pathlib2 import Path

from src.conf.settings import SettingsPatcher
from .base import AppTestCase


class ExposureSummary(AppTestCase):
    def test_several_exposures_exist___all_exposure_names_and_sizes_are_returned(self):
        with TemporaryDirectory() as inputs_dir:
            with SettingsPatcher(INPUTS_DATA_DIRECTORY=inputs_dir):
                self.create_input_file('test1.tar', 100)
                self.create_input_file('test2.tar', 200)
                self.create_input_file('test3.tar', 300)
                self.create_input_file('test4.tar', 400)

                response = self.app.get("/exposure_summary")

                self.assertEqual(response._status_code, 200)
                exposures = json.loads(response.data.decode('utf-8'))['exposures']

                self.assertEqual(len(exposures), 4)
                self.assertEqual(exposures[0]['location'], 'test1')
                self.assertEqual(exposures[0]['size'], 100)
                self.assertEqual(exposures[1]['location'], 'test2')
                self.assertEqual(exposures[1]['size'], 200)
                self.assertEqual(exposures[2]['location'], 'test3')
                self.assertEqual(exposures[2]['size'], 300)
                self.assertEqual(exposures[3]['location'], 'test4')
                self.assertEqual(exposures[3]['size'], 400)

    @given(text(alphabet=string.ascii_letters, min_size=1), integers(min_value=1, max_value=200))
    def test_get_exposure_summary_for_a_particular_location___correct_location_name_and_size_are_returned(self, location, size):
        with TemporaryDirectory() as inputs_dir:
            with SettingsPatcher(INPUTS_DATA_DIRECTORY=inputs_dir):
                self.create_input_file('{}.tar'.format(location), size)

                response = self.app.get("/exposure_summary/{}".format(location))

                self.assertEqual(response._status_code, 200)

                exposures = json.loads(response.data.decode('utf-8'))['exposures']
                self.assertEqual(len(exposures), 1)
                self.assertEqual(exposures[0]['location'], location)
                self.assertEqual(exposures[0]['size'], size)

    @given(text(alphabet=string.ascii_letters, min_size=1), integers(min_value=1, max_value=200))
    def test_get_exposure_summary_for_a_particular_location_that_does_not_exist___exposures_are_empty(self, location, size):
        with TemporaryDirectory() as inputs_dir:
            with SettingsPatcher(INPUTS_DATA_DIRECTORY=inputs_dir):
                self.create_input_file('other_{}.tar'.format(location), size)

                response = self.app.get("/exposure_summary/{}".format(location))

                self.assertEqual(response._status_code, 404)


class Exposure(AppTestCase):
    @given(text(alphabet=string.ascii_letters, min_size=1), binary(min_size=1, max_size=200))
    def test_location_exists___response_contains_tar_data(self, location, data):
        with TemporaryDirectory() as inputs_dir:
            with SettingsPatcher(INPUTS_DATA_DIRECTORY=inputs_dir):
                self.create_input_file('{}.tar'.format(location), data=data)
                response = self.app.get("/exposure/{}".format(location))

                self.assertEqual(response._status_code, 200)
                self.assertEqual(response.data, data)

    def test_location_does_not_exist___response_is_404(self):
        with TemporaryDirectory() as inputs_dir:
            with SettingsPatcher(INPUTS_DATA_DIRECTORY=inputs_dir):
                Path(os.path.join(inputs_dir, 'test1.tar')).touch()
                response = self.app.get("/exposure/test2")
                self.assertEqual(response._status_code, 404)

    @given(binary(min_size=1, max_size=200))
    def test_exposure_file_is_posted___exposure_is_stored_in_inputs_directory(self, data):
        with TemporaryDirectory() as inputs_dir, TemporaryDirectory() as upload_directory:
            with SettingsPatcher(INPUTS_DATA_DIRECTORY=inputs_dir):
                filepath = os.path.join(upload_directory, 'file.tar')
                self.create_input_file(filepath, data=data)

                with io.open(filepath, 'rb') as file_to_upload:
                    response = self.app.post(
                        "/exposure",
                        data={
                            'file': (file_to_upload, filepath),
                        },
                        content_type='multipart/form-data'
                    )
                    location = json.loads(response.data.decode('utf-8'))['exposures'][0]['location']

                response = self.app.get("/exposure/{}".format(location))
                self.assertEqual(response._status_code, 200)
                self.assertEqual(response.data, data)

    def test_no_location_is_given_on_delete___all_exposures_are_deleted(self):
        with TemporaryDirectory() as inputs_dir:
            with SettingsPatcher(INPUTS_DATA_DIRECTORY=inputs_dir):
                Path(os.path.join(inputs_dir, 'test1.tar')).touch()
                Path(os.path.join(inputs_dir, 'test2.tar')).touch()

                self.app.delete("/exposure")

                response = self.app.get("/exposure_summary")
                exposures = json.loads(response.data.decode('utf-8'))['exposures']

                self.assertEqual(response._status_code, 200)
                self.assertEqual(len(exposures), 0)

    def test_no_location_is_given_on_delete___non_tar_files_and_child_dirs_are_left(self):
        with TemporaryDirectory() as inputs_dir:
            with SettingsPatcher(INPUTS_DATA_DIRECTORY=inputs_dir):
                Path(os.path.join(inputs_dir, 'test1.tar')).touch()
                Path(os.path.join(inputs_dir, 'test2.tar')).touch()
                Path(os.path.join(inputs_dir, 'test.nottar')).touch()
                os.makedirs(os.path.join(inputs_dir, 'child.tar'))
                Path(os.path.join(inputs_dir, 'child.tar', 'test3.tar')).touch()

                self.app.delete("/exposure")

                self.assertTrue(os.path.exists(os.path.join(inputs_dir, 'test.nottar')))
                self.assertTrue(os.path.exists(os.path.join(inputs_dir, 'child.tar', 'test3.tar')))

    @given(lists(text(alphabet=string.ascii_letters, min_size=1), unique=True, min_size=2, max_size=2))
    def test_location_is_given_on_delete___only_named_location_is_deleted(self, locations):
        first_location, second_location = locations

        with TemporaryDirectory() as inputs_dir:
            with SettingsPatcher(INPUTS_DATA_DIRECTORY=inputs_dir):
                Path(os.path.join(inputs_dir, '{}.tar'.format(first_location))).touch()
                Path(os.path.join(inputs_dir, '{}.tar'.format(second_location))).touch()

                response = self.app.delete("/exposure/{}".format(first_location))
                self.assertEqual(response._status_code, 200)

                response = self.app.get("/exposure_summary")
                exposures = json.loads(response.data.decode('utf-8'))['exposures']

                self.assertEqual(len(exposures), 1)
                self.assertEqual(second_location, exposures[0]['location'])

    @given(lists(text(alphabet=string.ascii_letters, min_size=1), unique=True, min_size=2, max_size=2))
    def test_location_does_not_exist_on_delete___response_is_404(self, locations):
        first_location, second_location = locations

        with TemporaryDirectory() as inputs_dir:
            with SettingsPatcher(INPUTS_DATA_DIRECTORY=inputs_dir):
                Path(os.path.join(inputs_dir, '{}.tar'.format(first_location))).touch()

                response = self.app.delete("/exposure/{}".format(second_location))
                self.assertEqual(response._status_code, 404)

                response = self.app.get("/exposure_summary")
                exposures = json.loads(response.data.decode('utf-8'))['exposures']

                self.assertEqual(len(exposures), 1)
                self.assertEqual(first_location, exposures[0]['location'])
