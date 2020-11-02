import json
import mimetypes
import string

from backports.tempfile import TemporaryDirectory
from django.test import override_settings
from django.urls import reverse
from django_webtest import WebTestMixin
from hypothesis import given, settings
from hypothesis.extra.django import TestCase
from hypothesis.strategies import text, binary, sampled_from
from mock import patch
from rest_framework_simplejwt.tokens import AccessToken

from ...files.tests.fakes import fake_related_file
from ...analysis_models.tests.fakes import fake_analysis_model
from ...analyses.models import Analysis
from ...auth.tests.fakes import fake_user
from ..models import Portfolio
from .fakes import fake_portfolio

# Override default deadline for all tests to 8s
settings.register_profile("ci", deadline=800.0)
settings.load_profile("ci")


class PortfolioApi(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        portfolio = fake_portfolio()

        response = self.app.get(portfolio.get_absolute_url(), expect_errors=True)
        self.assertIn(response.status_code, [401,403])

    def test_user_is_authenticated_object_does_not_exist___response_is_404(self):
        user = fake_user()
        portfolio = fake_portfolio()

        response = self.app.get(
            reverse('portfolio-detail', kwargs={'version': 'v1', 'pk': portfolio.pk + 1}),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(404, response.status_code)

    def test_name_is_not_provided___response_is_400(self):
        user = fake_user()

        response = self.app.post(
            reverse('portfolio-list', kwargs={'version': 'v1'}),
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
            reverse('portfolio-list', kwargs={'version': 'v1'}),
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
        self.maxDiff = None
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()

                response = self.app.post(
                    reverse('portfolio-list', kwargs={'version': 'v1'}),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    params=json.dumps({'name': name}),
                    content_type='application/json'
                )
                self.assertEqual(201, response.status_code)

                portfolio = Portfolio.objects.get(pk=response.json['id'])
                portfolio.accounts_file = fake_related_file()
                portfolio.location_file = fake_related_file()
                portfolio.reinsurance_scope_file = fake_related_file()
                portfolio.reinsurance_info_file = fake_related_file()
                portfolio.save()

                response = self.app.get(
                    portfolio.get_absolute_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(200, response.status_code)
                self.assertEqual({
                    'id': portfolio.pk,
                    'name': name,
                    'created': portfolio.created.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                    'modified': portfolio.modified.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                    'accounts_file': {
                        "uri": response.request.application_url + portfolio.get_absolute_accounts_file_url(),
                        "name": portfolio.accounts_file.filename,
                        "stored": str(portfolio.accounts_file.file)
                    },
                    'location_file': {
                        "uri": response.request.application_url + portfolio.get_absolute_location_file_url(),
                        "name": portfolio.location_file.filename,
                        "stored": str(portfolio.location_file.file)
                    },
                    'reinsurance_info_file': {
                        "uri": response.request.application_url + portfolio.get_absolute_reinsurance_info_file_url(),
                        "name": portfolio.reinsurance_info_file.filename,
                        "stored": str(portfolio.reinsurance_info_file.file)
                    },
                    'reinsurance_scope_file': {
                        "uri": response.request.application_url + portfolio.get_absolute_reinsurance_scope_file_url(),
                        "name": portfolio.reinsurance_scope_file.filename,
                        "stored": str(portfolio.reinsurance_scope_file.file)
                    },
                    'storage_links': response.request.application_url + portfolio.get_absolute_storage_url()
                }, response.json)


class PortfolioApiCreateAnalysis(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        portfolio = fake_portfolio()

        response = self.app.get(portfolio.get_absolute_create_analysis_url(), expect_errors=True)
        self.assertIn(response.status_code, [401,403])

    def test_user_is_authenticated_object_does_not_exist___response_is_404(self):
        user = fake_user()
        portfolio = fake_portfolio()

        response = self.app.post(
            reverse('portfolio-create-analysis', kwargs={'version': 'v1', 'pk': portfolio.pk + 1}),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(404, response.status_code)

    def test_name_is_not_provided___response_is_400(self):
        user = fake_user()
        model = fake_analysis_model()
        portfolio = fake_portfolio()

        response = self.app.post(
            portfolio.get_absolute_create_analysis_url(),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params={'model': model.pk},
            content_type='application/json',
        )

        self.assertEqual(400, response.status_code)

    def test_portfolio_does_not_have_location_file_set___response_is_400(self):
        user = fake_user()
        model = fake_analysis_model()
        portfolio = fake_portfolio()

        response = self.app.post(
            portfolio.get_absolute_create_analysis_url(),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'name': 'name', 'model': model.pk}),
            content_type='application/json',
        )

        self.assertEqual(400, response.status_code)
        self.assertIn('"location_file" must not be null', response.json['portfolio'])

    def test_model_is_not_provided___response_is_400(self):
        user = fake_user()
        portfolio = fake_portfolio()

        response = self.app.post(
            portfolio.get_absolute_create_analysis_url(),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'name': 'name'}),
            content_type='application/json',
        )

        self.assertEqual(400, response.status_code)

    def test_model_does_not_exist___response_is_400(self):
        user = fake_user()
        portfolio = fake_portfolio()
        model = fake_analysis_model()

        response = self.app.post(
            portfolio.get_absolute_create_analysis_url(),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'name': 'name', 'model': model.pk + 1}),
            content_type='application/json',
        )

        self.assertEqual(400, response.status_code)

    @given(name=text(alphabet=' \t\n\r', max_size=10))
    def test_cleaned_name_is_empty___response_is_400(self, name):
        user = fake_user()
        model = fake_analysis_model()
        portfolio = fake_portfolio()

        response = self.app.post(
            portfolio.get_absolute_create_analysis_url(),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'name': name, 'model': model.pk}),
            content_type='application/json'
        )

        self.assertEqual(400, response.status_code)

    @given(name=text(alphabet=string.ascii_letters, max_size=10, min_size=1))
    def test_cleaned_name_and_model_are_present___object_is_created_inputs_are_generated(self, name):
        with patch('src.server.oasisapi.analyses.models.Analysis.generate_inputs', autospec=True) as generate_mock:
            with TemporaryDirectory() as d:
                with override_settings(MEDIA_ROOT=d):
                    self.maxDiff = None

                    user = fake_user()
                    model = fake_analysis_model()
                    portfolio = fake_portfolio(location_file=fake_related_file())

                    response = self.app.post(
                        portfolio.get_absolute_create_analysis_url(),
                        headers={
                            'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                        },
                        params=json.dumps({'name': name, 'model': model.pk}),
                        content_type='application/json'
                    )
                    self.assertEqual(201, response.status_code)

                    analysis = Analysis.objects.get(pk=response.json['id'])
                    analysis.settings_file = fake_related_file()
                    analysis.input_file = fake_related_file()
                    analysis.lookup_errors_file = fake_related_file()
                    analysis.lookup_success_file = fake_related_file()
                    analysis.lookup_validation_file = fake_related_file()
                    analysis.input_generation_traceback_file = fake_related_file()
                    analysis.output_file = fake_related_file()
                    analysis.run_traceback_file = fake_related_file()
                    analysis.save()

                    response = self.app.get(
                        analysis.get_absolute_url(),
                        headers={
                            'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                        },
                    )

                    self.assertEqual(200, response.status_code)
                    self.assertEqual(response.json['id'], analysis.pk)
                    self.assertEqual(response.json['created'], analysis.created.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
                    self.assertEqual(response.json['modified'], analysis.modified.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
                    self.assertEqual(response.json['name'], name)
                    self.assertEqual(response.json['portfolio'], portfolio.pk)
                    self.assertEqual(response.json['model'], model.pk)
                    self.assertEqual(response.json['settings_file'], response.request.application_url + analysis.get_absolute_settings_file_url())
                    self.assertEqual(response.json['input_file'], response.request.application_url + analysis.get_absolute_input_file_url())
                    self.assertEqual(response.json['lookup_errors_file'], response.request.application_url + analysis.get_absolute_lookup_errors_file_url())
                    self.assertEqual(response.json['lookup_success_file'], response.request.application_url + analysis.get_absolute_lookup_success_file_url())
                    self.assertEqual(response.json['lookup_validation_file'], response.request.application_url + analysis.get_absolute_lookup_validation_file_url())
                    self.assertEqual(response.json['input_generation_traceback_file'], response.request.application_url + analysis.get_absolute_input_generation_traceback_file_url())
                    self.assertEqual(response.json['output_file'], response.request.application_url + analysis.get_absolute_output_file_url())
                    self.assertEqual(response.json['run_traceback_file'], response.request.application_url + analysis.get_absolute_run_traceback_file_url())
                    generate_mock.assert_called_once_with(analysis, user)


class PortfolioAccountsFile(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        portfolio = fake_portfolio()

        response = self.app.get(portfolio.get_absolute_accounts_file_url(), expect_errors=True)
        self.assertIn(response.status_code, [401,403])

    def test_accounts_file_is_not_present___get_response_is_404(self):
        user = fake_user()
        portfolio = fake_portfolio()

        response = self.app.get(
            portfolio.get_absolute_accounts_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_accounts_file_is_not_present___delete_response_is_404(self):
        user = fake_user()
        portfolio = fake_portfolio()

        response = self.app.delete(
            portfolio.get_absolute_accounts_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_accounts_file_is_not_a_valid_format___response_is_400(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                portfolio = fake_portfolio()

                response = self.app.post(
                    portfolio.get_absolute_accounts_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file.tar', b'content'),
                    ),
                    expect_errors=True,
                )

                self.assertEqual(400, response.status_code)

    @given(file_content=binary(min_size=1), content_type=sampled_from(['text/csv', 'application/json']))
    def test_accounts_file_is_uploaded___file_can_be_retrieved(self, file_content, content_type):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                portfolio = fake_portfolio()

                self.app.post(
                    portfolio.get_absolute_accounts_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                )

                response = self.app.get(
                    portfolio.get_absolute_accounts_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(response.body, file_content)
                self.assertEqual(response.content_type, content_type)


class PortfolioLocationFile(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        portfolio = fake_portfolio()

        response = self.app.get(portfolio.get_absolute_location_file_url(), expect_errors=True)
        self.assertIn(response.status_code, [401,403])

    def test_location_file_is_not_present___get_response_is_404(self):
        user = fake_user()
        portfolio = fake_portfolio()

        response = self.app.get(
            portfolio.get_absolute_location_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_location_file_is_not_present___delete_response_is_404(self):
        user = fake_user()
        portfolio = fake_portfolio()

        response = self.app.delete(
            portfolio.get_absolute_location_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_location_file_is_not_a_valid_format___response_is_400(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                portfolio = fake_portfolio()

                response = self.app.post(
                    portfolio.get_absolute_location_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file.tar', b'content'),
                    ),
                    expect_errors=True,
                )

                self.assertEqual(400, response.status_code)

    @given(file_content=binary(min_size=1), content_type=sampled_from(['text/csv', 'application/json']))
    def test_location_file_is_uploaded___file_can_be_retrieved(self, file_content, content_type):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                portfolio = fake_portfolio()

                self.app.post(
                    portfolio.get_absolute_location_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                )

                response = self.app.get(
                    portfolio.get_absolute_location_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(response.body, file_content)
                self.assertEqual(response.content_type, content_type)


class PortfolioReinsuranceSourceFile(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        portfolio = fake_portfolio()

        response = self.app.get(portfolio.get_absolute_reinsurance_scope_file_url(), expect_errors=True)
        self.assertIn(response.status_code, [401,403])

    def test_reinsurance_scope_file_is_not_present___get_response_is_404(self):
        user = fake_user()
        portfolio = fake_portfolio()

        response = self.app.get(
            portfolio.get_absolute_reinsurance_scope_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_reinsurance_scope_file_is_not_present___delete_response_is_404(self):
        user = fake_user()
        portfolio = fake_portfolio()

        response = self.app.delete(
            portfolio.get_absolute_reinsurance_scope_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_reinsurance_scope_file_is_not_a_valid_format___response_is_400(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                portfolio = fake_portfolio()

                response = self.app.post(
                    portfolio.get_absolute_reinsurance_scope_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file.tar', b'content'),
                    ),
                    expect_errors=True,
                )

                self.assertEqual(400, response.status_code)

    @given(file_content=binary(min_size=1), content_type=sampled_from(['text/csv', 'application/json']))
    def test_reinsurance_scope_file_is_uploaded___file_can_be_retrieved(self, file_content, content_type):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                portfolio = fake_portfolio()

                self.app.post(
                    portfolio.get_absolute_reinsurance_scope_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                )

                response = self.app.get(
                    portfolio.get_absolute_reinsurance_scope_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(response.body, file_content)
                self.assertEqual(response.content_type, content_type)


class PortfolioReinsuranceInfoFile(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        portfolio = fake_portfolio()

        response = self.app.get(portfolio.get_absolute_reinsurance_info_file_url(), expect_errors=True)
        self.assertIn(response.status_code, [401,403])

    def test_reinsurance_info_file_is_not_present___get_response_is_404(self):
        user = fake_user()
        portfolio = fake_portfolio()

        response = self.app.get(
            portfolio.get_absolute_reinsurance_info_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_reinsurance_info_file_is_not_present___delete_response_is_404(self):
        user = fake_user()
        portfolio = fake_portfolio()

        response = self.app.delete(
            portfolio.get_absolute_reinsurance_info_file_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_reinsurance_info_file_is_not_a_valid_format___response_is_400(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                portfolio = fake_portfolio()

                response = self.app.post(
                    portfolio.get_absolute_reinsurance_info_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file.tar', b'content'),
                    ),
                    expect_errors=True,
                )

                self.assertEqual(400, response.status_code)

    @given(file_content=binary(min_size=1), content_type=sampled_from(['text/csv', 'application/json']))
    def test_reinsurance_info_file_is_uploaded___file_can_be_retrieved(self, file_content, content_type):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                portfolio = fake_portfolio()

                self.app.post(
                    portfolio.get_absolute_reinsurance_info_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                )

                response = self.app.get(
                    portfolio.get_absolute_reinsurance_info_file_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(response.body, file_content)
                self.assertEqual(response.content_type, content_type)
