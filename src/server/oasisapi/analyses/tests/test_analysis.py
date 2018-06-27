import json
import mimetypes
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

from ...files.tests.fakes import fake_related_file
from ...analysis_models.tests.fakes import fake_analysis_model
from ...portfolios.tests.fakes import fake_portfolio
from ...auth.tests.fakes import fake_user
from ..models import Analysis
from .fakes import fake_analysis


class FakeAsyncResultFactory(object):
    def __init__(self, target_task_id):
        self.target_task_id = target_task_id
        self.revoke_kwargs = {}
        self.revoke_called = False

        class FakeAsyncResult(object):
            def __init__(_self, task_id):
                if task_id != target_task_id:
                    raise ValueError()

            def revoke(_self, **kwargs):
                self.revoke_called = True
                self.revoke_kwargs = kwargs

        self.fake_res = FakeAsyncResult

    def __call__(self, task_id):
        return self.fake_res(task_id)


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
    def test_cleaned_name_portfolio_and_model_are_present___object_is_created(self, name):
        user = fake_user()
        model = fake_analysis_model()
        portfolio = fake_portfolio()

        response = self.app.post(
            reverse('analysis-list'),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'name': name, 'portfolio': portfolio.pk, 'model': model.pk}),
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
            'model': model.pk,
            'settings_file': response.request.application_url + analysis.get_absolute_settings_file_url(),
            'input_file': response.request.application_url + analysis.get_absolute_input_file_url(),
            'input_errors_file': response.request.application_url + analysis.get_absolute_input_errors_file_url(),
            'output_file': response.request.application_url + analysis.get_absolute_output_file_url(),
            'status': Analysis.status_choices.NOT_RAN,
        }, response.json)

    def test_model_does_not_exist___response_is_400(self):
        user = fake_user()
        analysis = fake_analysis()
        model = fake_analysis_model()

        response = self.app.patch(
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

        response = self.app.patch(
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
    def test_user_is_not_authenticated___response_is_401(self):
        analysis = fake_analysis()

        response = self.app.post(analysis.get_absolute_run_url(), expect_errors=True)

        self.assertEqual(401, response.status_code)

    def test_user_is_authenticated_object_does_not_exist___response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.post(
            reverse('analysis-run', args=[analysis.pk + 1]),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(404, response.status_code)

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
        with patch('src.server.oasisapi.analyses.models.poll_analysis_status') as poll_analysis_mock , patch('src.server.oasisapi.analyses.models.celery_app') as mock_celery:
            with TemporaryDirectory() as d:
                with override_settings(MEDIA_ROOT=d):
                    mock_celery.send_task.return_value = task_id

                    user = fake_user()
                    model = fake_analysis_model()
                    analysis = fake_analysis(
                        model=model,
                        status=status,
                        settings_file=fake_related_file(file=b'{}'),
                        input_file=fake_related_file(),
                    )

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

    @given(status=sampled_from([Analysis.status_choices.PENDING, Analysis.status_choices.STARTED, Analysis.status_choices.STOPPED_CANCELLED]))
    def test_required_inputs_are_present_status_is_in_progress___task_is_not_queued(self, status):
        with patch('src.server.oasisapi.analyses.models.poll_analysis_status') as poll_analysis_mock , patch('src.server.oasisapi.analyses.models.celery_app') as mock_celery:
            with TemporaryDirectory() as d:
                with override_settings(MEDIA_ROOT=d):
                    user = fake_user()
                    model = fake_analysis_model()
                    analysis = fake_analysis(
                        model=model,
                        status=status,
                        settings_file=fake_related_file(file=b'{}'),
                        input_file=fake_related_file(),
                    )

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


class AnalysisCancel(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_401(self):
        analysis = fake_analysis()

        response = self.app.post(analysis.get_absolute_cancel_url(), expect_errors=True)

        self.assertEqual(401, response.status_code)

    def test_user_is_authenticated_object_does_not_exist___response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.post(
            reverse('analysis-cancel', args=[analysis.pk + 1]),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(404, response.status_code)

    @given(
        status=sampled_from([Analysis.status_choices.NOT_RAN, Analysis.status_choices.STOPPED_COMPLETED, Analysis.status_choices.STOPPED_ERROR, Analysis.status_choices.STOPPED_CANCELLED]),
        task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
    )
    def test_state_is_not_running___revoke_is_not_called(self, status, task_id):
        res_factory = FakeAsyncResultFactory(task_id)

        with patch('src.server.oasisapi.analyses.models.AsyncResult', res_factory):
            user = fake_user()
            analysis = fake_analysis(status=status, task_id=task_id)

            response = self.app.post(
                analysis.get_absolute_cancel_url(),
                headers={
                    'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                },
                expect_errors=True,
            )

            analysis.refresh_from_db()

            self.assertEqual(400, response.status_code)
            self.assertEqual(status, analysis.status)
            self.assertFalse(res_factory.revoke_called)

    @given(
        status=sampled_from([Analysis.status_choices.PENDING, Analysis.status_choices.STARTED]),
        task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters),
    )
    def test_state_is_running___revoke_is_called(self, status, task_id):
        res_factory = FakeAsyncResultFactory(task_id)

        with patch('src.server.oasisapi.analyses.models.AsyncResult', res_factory):
            user = fake_user()
            analysis = fake_analysis(status=status, task_id=task_id)

            response = self.app.post(
                analysis.get_absolute_cancel_url(),
                headers={
                    'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                },
                expect_errors=True,
            )

            analysis.refresh_from_db()

            self.assertEqual(200, response.status_code)
            self.assertEqual(status, analysis.status)
            self.assertTrue(res_factory.revoke_called)
            self.assertEqual({'signal': 'SIGKILL', 'terminate': True}, res_factory.revoke_kwargs)


class AnalysisCopy(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_401(self):
        analysis = fake_analysis()

        response = self.app.post(analysis.get_absolute_copy_url(), expect_errors=True)

        self.assertEqual(401, response.status_code)

    def test_user_is_authenticated_object_does_not_exist___response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.post(
            reverse('analysis-copy', args=[analysis.pk + 1]),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(404, response.status_code)

    def test_new_object_is_created(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertNotEqual(analysis.pk, response.json['id'])

    @given(name=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
    def test_no_new_name_is_provided___copy_is_appended_to_name(self, name):
        user = fake_user()
        analysis = fake_analysis(name=name)

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(Analysis.objects.get(pk=response.json['id']).name, '{} - Copy'.format(name))

    @given(orig_name=text(min_size=1, max_size=10, alphabet=string.ascii_letters), new_name=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
    def test_new_name_is_provided___new_name_is_set_on_new_object(self, orig_name, new_name):
        user = fake_user()
        analysis = fake_analysis(name=orig_name)

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'name': new_name}),
            content_type='application/json'
        )

        self.assertEqual(Analysis.objects.get(pk=response.json['id']).name, new_name)

    @given(status=sampled_from(list(Analysis.status_choices._db_values)))
    def test_state_is_reset(self, status):
        user = fake_user()
        analysis = fake_analysis(status=status)

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(Analysis.objects.get(pk=response.json['id']).status, Analysis.status_choices.NOT_RAN)

    def test_creator_is_set_to_caller(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(Analysis.objects.get(pk=response.json['id']).creator, user)

    @given(task_id=text(min_size=1, max_size=10, alphabet=string.ascii_letters))
    def test_task_id_is_reset(self, task_id):
        user = fake_user()
        analysis = fake_analysis(task_id=task_id)

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(Analysis.objects.get(pk=response.json['id']).task_id, '')

    def test_portfolio_is_not_supplied___portfolio_is_copied(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(Analysis.objects.get(pk=response.json['id']).portfolio, analysis.portfolio)

    def test_portfolio_is_supplied___portfolio_is_replaced(self):
        user = fake_user()
        analysis = fake_analysis()
        new_portfolio = fake_portfolio()

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'portfolio': new_portfolio.pk}),
            content_type='application/json',
        )

        self.assertEqual(Analysis.objects.get(pk=response.json['id']).portfolio, new_portfolio)

    def test_model_is_not_supplied___model_is_copied(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(Analysis.objects.get(pk=response.json['id']).model, analysis.model)

    def test_model_is_supplied___model_is_replaced(self):
        user = fake_user()
        analysis = fake_analysis()
        new_model = fake_analysis_model()

        response = self.app.post(
            analysis.get_absolute_copy_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'model': new_model.pk}),
            content_type='application/json',
        )

        self.assertEqual(Analysis.objects.get(pk=response.json['id']).model, new_model)

    def test_settings_file_is_not_supplied___settings_file_is_copied(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis(settings_file=fake_related_file(file='{}'))

                response = self.app.post(
                    analysis.get_absolute_copy_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    }
                )

                self.assertEqual(Analysis.objects.get(pk=response.json['id']).settings_file.pk, analysis.settings_file.pk)

    def test_input_file_is_not_supplied___input_file_is_copied(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis(input_file=fake_related_file())

                response = self.app.post(
                    analysis.get_absolute_copy_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    }
                )

                self.assertEqual(Analysis.objects.get(pk=response.json['id']).input_file, analysis.input_file)

    def test_input_errors_file_is_cleared(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis(input_errors_file=fake_related_file())

                response = self.app.post(
                    analysis.get_absolute_copy_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertIsNone(Analysis.objects.get(pk=response.json['id']).input_errors_file)

    def test_output_file_is_cleared(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis(output_file=fake_related_file())

                response = self.app.post(
                    analysis.get_absolute_copy_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertIsNone(Analysis.objects.get(pk=response.json['id']).output_file)


class AnalysisSettingsFile(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_401(self):
        analysis = fake_analysis()

        response = self.app.get(analysis.get_absolute_settings_file_url(), expect_errors=True)

        self.assertEqual(401, response.status_code)

    def test_settings_file_is_not_present___get_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.get(
            analysis.get_absolute_settings_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_settings_file_is_not_present___delete_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.delete(
            analysis.get_absolute_settings_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_settings_file_is_not_a_valid_format___response_is_400(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis()

                response = self.app.post(
                    analysis.get_absolute_settings_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file.tar', b'content'),
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

                self.app.post(
                    analysis.get_absolute_settings_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file.json', file_content),
                    ),
                )

                response = self.app.get(
                    analysis.get_absolute_settings_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(response.body, file_content)
                self.assertEqual(response.content_type, 'application/json')


class AnalysisInputFile(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_401(self):
        analysis = fake_analysis()

        response = self.app.get(analysis.get_absolute_input_file_url(), expect_errors=True)

        self.assertEqual(401, response.status_code)

    def test_input_file_is_not_present___get_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.get(
            analysis.get_absolute_input_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_input_file_is_not_present___delete_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.delete(
            analysis.get_absolute_input_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_input_file_is_not_a_valid_format___response_is_400(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis()

                response = self.app.post(
                    analysis.get_absolute_input_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file.csv', b'content'),
                    ),
                    expect_errors=True,
                )

                self.assertEqual(400, response.status_code)

    @given(file_content=binary(min_size=1), content_type=sampled_from(['application/x-gzip', 'application/gzip', 'application/x-tar', 'application/tar']))
    def test_input_file_is_uploaded___file_can_be_retrieved(self, file_content, content_type):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis()

                self.app.post(
                    analysis.get_absolute_input_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content, content_type),
                    ),
                )

                response = self.app.get(
                    analysis.get_absolute_input_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(response.body, file_content)
                self.assertEqual(response.content_type, content_type)


class AnalysisInputErrorsFile(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_401(self):
        analysis = fake_analysis()

        response = self.app.get(analysis.get_absolute_input_errors_file_url(), expect_errors=True)

        self.assertEqual(401, response.status_code)

    def test_input_errors_file_is_not_present___get_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.get(
            analysis.get_absolute_input_errors_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_input_errors_file_is_not_present___delete_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.delete(
            analysis.get_absolute_input_errors_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_input_errors_file_is_not_valid_format___post_response_is_405(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis()

                response = self.app.post(
                    analysis.get_absolute_input_errors_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file.csv', b'content'),
                    ),
                    expect_errors=True,
                )

                self.assertEqual(405, response.status_code)

    @given(file_content=binary(min_size=1), content_type=sampled_from(['text/csv', 'application/json']))
    def test_input_errors_file_is_present___file_can_be_retrieved(self, file_content, content_type):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis(input_errors_file=fake_related_file(file=file_content, content_type=content_type))

                response = self.app.get(
                    analysis.get_absolute_input_errors_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(response.body, file_content)
                self.assertEqual(response.content_type, content_type)


class AnalysisOutputFile(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_401(self):
        analysis = fake_analysis()

        response = self.app.get(analysis.get_absolute_output_file_url(), expect_errors=True)

        self.assertEqual(401, response.status_code)

    def test_output_file_is_not_present___get_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.get(
            analysis.get_absolute_output_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_output_file_is_not_present___delete_response_is_404(self):
        user = fake_user()
        analysis = fake_analysis()

        response = self.app.delete(
            analysis.get_absolute_output_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_output_file_is_not_valid_format___post_response_is_405(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis()

                response = self.app.post(
                    analysis.get_absolute_output_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file.csv', b'content'),
                    ),
                    expect_errors=True,
                )

                self.assertEqual(405, response.status_code)

    @given(file_content=binary(min_size=1), content_type=sampled_from(['application/x-gzip', 'application/gzip', 'application/x-tar', 'application/tar']))
    def test_output_file_is_present___file_can_be_retrieved(self, file_content, content_type):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                analysis = fake_analysis(output_file=fake_related_file(file=file_content, content_type=content_type))

                response = self.app.get(
                    analysis.get_absolute_output_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(response.body, file_content)
                self.assertEqual(response.content_type, content_type)
