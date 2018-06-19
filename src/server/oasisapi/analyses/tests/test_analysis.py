import json
import string
from tempfile import NamedTemporaryFile

from backports.tempfile import TemporaryDirectory
from django.core.files import File
from django.test import override_settings
from django.urls import reverse
from django_webtest import WebTestMixin
from hypothesis import given
from hypothesis.extra.django import TestCase
from hypothesis.strategies import text, binary, sampled_from
from mock import patch
from rest_framework_simplejwt.tokens import AccessToken

from ...analysis_models.tests.fakes import fake_analysis_model
from ...portfolios.tests.fakes import fake_portfolio
from ...auth.tests.fakes import fake_user
from ..models import Analysis
from .fakes import fake_analysis


class AnalysisApi(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_401(self):
        analysis = fake_analysis()

        response = self.app.get(analysis.get_absolute_url(), expect_errors=True)

        self.assertEqual(401, response.status_code)

    def test_user_is_authenticated_object_does_not_exist___response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.get(
            reverse('analysis-detail', args=[analysis.pk + 1]),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(404, response.status_code)

    def test_name_is_not_provided___response_is_400(self):
        user = fake_user()

        response = self.app.post(
            reverse('analysis-list'),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params={},
            content_type='application/json',
        )

        self.assertEqual(400, response.status_code)

    @given(name=text(alphabet=' \t\n\r', max_size=10))
    def test_cleaned_name_is_empty___response_is_400(self, name):
        user = fake_user()

        response = self.app.post(
            reverse('analysis-list'),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'name': name}),
            content_type='application/json'
        )

        self.assertEqual(400, response.status_code)

    @given(name=text(alphabet=string.ascii_letters, max_size=10, min_size=1))
    def test_cleaned_name_is_present___object_is_created(self, name):
        user = fake_user()
        portfolio = fake_portfolio()

        response = self.app.post(
            reverse('analysis-list'),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'name': name, 'portfolio': portfolio.pk}),
            content_type='application/json'
        )
        self.assertEqual(201, response.status_code)

        analysis = Analysis.objects.get(pk=response.json['id'])
        response = self.app.get(
            analysis.get_absolute_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual({
            'created': analysis.created.strftime('%y-%m-%dT%H:%M:%S.%f%z'),
            'modified': analysis.modified.strftime('%y-%m-%dT%H:%M:%S.%f%z'),
            'id': analysis.pk,
            'name': name,
            'portfolio': portfolio.pk,
            'model': None,
            'settings_file': None,
            'input_file': None,
            'input_errors_file': None,
            'output_file': None,
            'status': Analysis.status_choices.NOT_RAN,
        }, response.json)

    def test_settings_file_is_not_a_valid_format___response_is_400(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis()

                response = self.app.put(
                    analysis.get_absolute_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('settings_file', 'file.tar', b'content'),
                    ),
                    expect_errors=True,
                )

                self.assertEqual(400, response.status_code)

    @given(file_content=binary(min_size=1))
    def test_settings_file_is_uploaded___file_can_be_retrieved(self, file_content):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis()

                response = self.app.put(
                    analysis.get_absolute_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('settings_file', 'file.json', file_content,),
                    ),
                    content_type='application/json'
                )

                analysis.refresh_from_db()

                self.assertEqual(200, response.status_code)
                self.assertEqual(analysis.settings_file.read(), file_content)
                self.assertEqual(response.json['settings_file'], response.request.application_url + analysis.settings_file.url)

    def test_input_file_is_not_a_valid_format___response_is_400(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis()

                response = self.app.put(
                    analysis.get_absolute_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('input_file', 'file.csv', b'content'),
                    ),
                    expect_errors=True,
                )

                self.assertEqual(400, response.status_code)

    @given(file_content=binary(min_size=1))
    def test_input_file_is_uploaded___file_can_be_retrieved(self, file_content):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis()

                response = self.app.put(
                    analysis.get_absolute_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('input_file', 'file.tar', file_content,),
                    ),
                    content_type='application/json'
                )

                analysis.refresh_from_db()

                self.assertEqual(200, response.status_code)
                self.assertEqual(analysis.input_file.read(), file_content)
                self.assertEqual(response.json['input_file'], response.request.application_url + analysis.input_file.url)

    def test_model_does_not_exist___response_is_400(self):
        user = fake_user()
        analysis = fake_analysis()
        model = fake_analysis_model()

        response = self.app.put(
            analysis.get_absolute_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'model': model.pk + 1}),
            content_type='application/json',
            expect_errors=True,
        )

        self.assertEqual(400, response.status_code)

    def test_model_does_exist___response_is_200(self):
        user = fake_user()
        analysis = fake_analysis()
        model = fake_analysis_model()

        response = self.app.put(
            analysis.get_absolute_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'model': model.pk}),
            content_type='application/json',
            expect_errors=True,
        )

        analysis.refresh_from_db()

        self.assertEqual(200, response.status_code)
        self.assertEqual(analysis.model, model)


class AnalysisRun(WebTestMixin, TestCase):
    def test_model_is_not_set___error_is_written_to_file_status_is_error(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.post(
            analysis.get_absolute_run_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        analysis.refresh_from_db()

        self.assertEqual(400, response.status_code)
        self.assertIn(
            '"model" is not set on the analysis object',
            json.loads(analysis.input_errors_file.read())['errors'],
        )
        self.assertEqual(Analysis.status_choices.STOPPED_ERROR, analysis.status)

    def test_input_file_is_not_set___error_is_written_to_file_status_is_error(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.post(
            analysis.get_absolute_run_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        analysis.refresh_from_db()

        self.assertEqual(400, response.status_code)
        self.assertIn(
            '"input_file" is not set on the analysis object',
            json.loads(analysis.input_errors_file.read())['errors'],
        )
        self.assertEqual(Analysis.status_choices.STOPPED_ERROR, analysis.status)

    def test_settings_file_is_not_set___error_is_written_to_file_status_is_error(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.post(
            analysis.get_absolute_run_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        analysis.refresh_from_db()

        self.assertEqual(400, response.status_code)
        self.assertIn(
            '"settings_file" is not set on the analysis object',
            json.loads(analysis.input_errors_file.read())['errors'],
        )
        self.assertEqual(Analysis.status_choices.STOPPED_ERROR, analysis.status)

    @given(task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters), status=sampled_from([Analysis.status_choices.STOPPED_COMPLETED, Analysis.status_choices.STOPPED_ERROR, Analysis.status_choices.NOT_RAN]))
    def test_required_inputs_are_present_status_is_not_in_progress___task_is_added(self, task_id, status):
        with patch('oasisapi.analyses.models.poll_analysis_status') as poll_analysis_mock , patch('oasisapi.analyses.models.celery_app') as mock_celery:
            with TemporaryDirectory() as d:
                with override_settings(MEDIA_ROOT=d):
                    mock_celery.send_task.return_value = task_id

                    user = fake_user()
                    model = fake_analysis_model()
                    analysis = fake_analysis(model=model, status=status)

                    with NamedTemporaryFile('w+') as settings, NamedTemporaryFile('w+') as inputs:
                        settings.write('{}')
                        analysis.settings_file = File(inputs, '{}.json'.format(settings.name))

                        inputs.write('{}')
                        analysis.input_file = File(inputs, '{}.json'.format(inputs.name))

                        analysis.save()

                    response = self.app.post(
                        analysis.get_absolute_run_url(),
                        headers={
                            'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                        },
                    )

                    analysis.refresh_from_db()

                    self.assertEqual(200, response.status_code)
                    self.assertFalse(analysis.input_errors_file)
                    self.assertEqual(Analysis.status_choices.PENDING, analysis.status)
                    mock_celery.send_task.assert_called_once_with(
                        'run_analysis',
                        (response.json['input_file'], [json.loads(analysis.settings_file.read())]),
                        queue='{}-{}'.format(model.supplier_id, model.version_id)
                    )
                    poll_analysis_mock.delay.assert_called_once_with(analysis.pk)

    @given(status=sampled_from([Analysis.status_choices.PENDING, Analysis.status_choices.STARTED]))
    def test_required_inputs_are_present_status_is_in_progress___task_is_not_queued(self, status):
        with patch('oasisapi.analyses.models.poll_analysis_status') as poll_analysis_mock , patch('oasisapi.analyses.models.celery_app') as mock_celery:
            with TemporaryDirectory() as d:
                with override_settings(MEDIA_ROOT=d):
                    user = fake_user()
                    model = fake_analysis_model()
                    analysis = fake_analysis(model=model, status=status)

                    with NamedTemporaryFile('w+') as settings, NamedTemporaryFile('w+') as inputs:
                        settings.write('{}')
                        analysis.settings_file = File(inputs, '{}.json'.format(settings.name))

                        inputs.write('{}')
                        analysis.input_file = File(inputs, '{}.json'.format(inputs.name))

                        analysis.save()

                    response = self.app.post(
                        analysis.get_absolute_run_url(),
                        headers={
                            'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                        },
                        expect_errors=True,
                    )

                    analysis.refresh_from_db()

                    self.assertEqual(400, response.status_code)
                    self.assertFalse(analysis.input_errors_file)
                    mock_celery.send_task.assert_not_called()
                    poll_analysis_mock.delay.assert_not_called()
