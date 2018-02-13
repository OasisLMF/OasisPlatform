#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import string
from collections import namedtuple

from backports.tempfile import TemporaryDirectory
from flask import json
from hypothesis import given
from hypothesis.strategies import text, integers
from mock import patch, Mock
from oasislmf.utils import status

from src.settings import SettingsPatcher
from .base import AppTestCase


class PostAnalysis(AppTestCase):
    def test_no_data_is_provided___response_is_400(self):
        with TemporaryDirectory() as inputs_dir:
            with SettingsPatcher(INPUTS_DATA_DIRECTORY=inputs_dir):
                self.create_input_file('test.tar', 100)

                response = self.app.post('/analysis/test')

                self.assertEqual(response._status_code, 400)

    def test_analysis_settings_are_missing_from_post_data___response_is_400(self):
        with TemporaryDirectory() as inputs_dir:
            with SettingsPatcher(INPUTS_DATA_DIRECTORY=inputs_dir):
                self.create_input_file('test.tar', 100)

                response = self.app.post(
                    '/analysis/test',
                    data=json.dumps({}),
                    content_type='application/json',
                )

                self.assertEqual(response._status_code, 400)

    def test_module_supplier_id_is_missing_from_post_data___response_is_400(self):
        with TemporaryDirectory() as inputs_dir:
            with SettingsPatcher(INPUTS_DATA_DIRECTORY=inputs_dir):
                self.create_input_file('test.tar', 100)

                response = self.app.post(
                    '/analysis/test',
                    data=json.dumps({
                        'analysis_settings': {'model_version_id': 'version'}
                    }),
                    content_type='application/json',
                )

                self.assertEqual(response._status_code, 400)

    def test_module_version_id_is_missing_from_post_data___response_is_400(self):
        with TemporaryDirectory() as inputs_dir:
            with SettingsPatcher(INPUTS_DATA_DIRECTORY=inputs_dir):
                self.create_input_file('test.tar', 100)

                response = self.app.post(
                    '/analysis/test',
                    data=json.dumps({'analysis_settings': {'module_supplier_id': 'supplier'}}),
                    content_type='application/json',
                )

                self.assertEqual(response._status_code, 400)

    @given(text(alphabet=string.ascii_letters, min_size=1), integers())
    def test_analysis_settings_are_valid___celery_task_is_started(self, location, task_id):
        with TemporaryDirectory() as inputs_dir, patch('src.server.app.CELERY') as celery_mock:
            with SettingsPatcher(INPUTS_DATA_DIRECTORY=inputs_dir):
                self.create_input_file('{}.tar'.format(location), 100)
                analysis_settings = {
                    'analysis_settings': {
                        'module_supplier_id': 'supplier',
                        'model_version_id': 'version',
                    },

                }

                celery_mock.send_task = Mock(return_value=namedtuple('Task', ['task_id'])(task_id))
                response = self.app.post(
                    '/analysis/{}'.format(location),
                    data=json.dumps(analysis_settings),
                    content_type='application/json',
                )

                celery_mock.send_task.assert_called_once_with(
                    'run_analysis',
                    (location, [analysis_settings]),
                    queue='supplier-version'
                )
                self.assertEqual(response._status_code, 200)


class AnalysisStatus(AppTestCase):
    fake_result = namedtuple('AsyncResult', ['result', 'state'])

    @patch('src.server.app.CELERY.AsyncResult', Mock(return_value=fake_result('output_location', status.STATUS_SUCCESS)))
    def test_celery_task_is_successful___result_is_successful(self):
        response = self.app.get('/analysis_status/{}'.format('location'))

        self.assertEqual(json.loads(response.data.decode('utf-8')), {
            'id': -1,
            'status': status.STATUS_SUCCESS,
            'message': '',
            'outputs_location': 'output_location',
        })

    @patch('src.server.app.CELERY.AsyncResult', Mock(return_value=fake_result('message', status.STATUS_PENDING)))
    def test_celery_task_is_pending___result_is_pending(self):
        response = self.app.get('/analysis_status/{}'.format('location'))

        self.assertEqual(json.loads(response.data.decode('utf-8')), {
            'id': -1,
            'status': status.STATUS_PENDING,
            'message': '',
            'outputs_location': None,
        })

    @patch('src.server.app.CELERY.AsyncResult', Mock(return_value=fake_result('message', status.STATUS_FAILURE)))
    def test_celery_task_is_failure___result_is_failure(self):
        response = self.app.get('/analysis_status/{}'.format('location'))

        self.assertEqual(json.loads(response.data.decode('utf-8')), {
            'id': -1,
            'status': status.STATUS_FAILURE,
            'message': "'message'",
            'outputs_location': None,
        })

    @patch('src.server.app.CELERY.AsyncResult', Mock(side_effect=[
        fake_result(None, status.STATUS_SUCCESS),
        fake_result('output_location', status.STATUS_SUCCESS),
    ]))
    def test_celery_task_is_successful_with_location_on_seccond_attempt___result_is_successful(self):
        response = self.app.get('/analysis_status/{}'.format('location'))

        self.assertEqual(json.loads(response.data.decode('utf-8')), {
            'id': -1,
            'status': status.STATUS_SUCCESS,
            'message': '',
            'outputs_location': 'output_location',
        })

    @patch('src.server.app.CELERY.AsyncResult', Mock(side_effect=[
        fake_result(None, status.STATUS_SUCCESS),
        fake_result(None, status.STATUS_SUCCESS),
    ]))
    def test_celery_task_is_successful_with_no_location_on_seccond_attempt___result_is_failure(self):
        response = self.app.get('/analysis_status/{}'.format('location'))

        self.assertEqual(json.loads(response.data.decode('utf-8')), {
            'id': -1,
            'status': status.STATUS_FAILURE,
            'message': '',
            'outputs_location': None,
        })
