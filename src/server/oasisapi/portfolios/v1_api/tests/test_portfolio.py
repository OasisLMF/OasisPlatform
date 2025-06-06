import json
import mimetypes
import string
import io
import pandas as pd

from backports.tempfile import TemporaryDirectory
from django.test import override_settings
from django.urls import reverse
from django_webtest import WebTestMixin
from hypothesis import given, settings
from hypothesis.extra.django import TestCase
from hypothesis.strategies import text, binary, sampled_from
from mock import patch
from rest_framework_simplejwt.tokens import AccessToken
from ods_tools.oed.exposure import OedExposure

from src.server.oasisapi.files.v1_api.tests.fakes import fake_related_file
from src.server.oasisapi.analysis_models.v1_api.tests.fakes import fake_analysis_model
from src.server.oasisapi.analyses.models import Analysis
from src.server.oasisapi.auth.tests.fakes import fake_user
from src.server.oasisapi.portfolios.models import Portfolio
from .fakes import fake_portfolio

# Override default deadline for all tests to 8s
settings.register_profile("ci", deadline=800.0)
settings.load_profile("ci")
NAMESPACE = 'v1-portfolios'


class PortfolioApi(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        portfolio = fake_portfolio()

        response = self.app.get(portfolio.get_absolute_url(namespace=NAMESPACE), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_user_is_authenticated_object_does_not_exist___response_is_404(self):
        user = fake_user()
        portfolio = fake_portfolio()

        response = self.app.get(
            reverse(f'{NAMESPACE}:portfolio-detail', kwargs={'pk': portfolio.pk + 1}),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            }
        )

        self.assertEqual(404, response.status_code)

    def test_name_is_not_provided___response_is_400(self):
        user = fake_user()

        response = self.app.post(
            reverse(f'{NAMESPACE}:portfolio-list'),
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
            reverse(f'{NAMESPACE}:portfolio-list'),
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
                    reverse(f'{NAMESPACE}:portfolio-list'),
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
                    portfolio.get_absolute_url(namespace=NAMESPACE),
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
                        "uri": response.request.application_url + portfolio.get_absolute_accounts_file_url(namespace=NAMESPACE),
                        "name": portfolio.accounts_file.filename,
                        "stored": str(portfolio.accounts_file.file)
                    },
                    'location_file': {
                        "uri": response.request.application_url + portfolio.get_absolute_location_file_url(namespace=NAMESPACE),
                        "name": portfolio.location_file.filename,
                        "stored": str(portfolio.location_file.file)
                    },
                    'reinsurance_info_file': {
                        "uri": response.request.application_url + portfolio.get_absolute_reinsurance_info_file_url(namespace=NAMESPACE),
                        "name": portfolio.reinsurance_info_file.filename,
                        "stored": str(portfolio.reinsurance_info_file.file)
                    },
                    'reinsurance_scope_file': {
                        "uri": response.request.application_url + portfolio.get_absolute_reinsurance_scope_file_url(namespace=NAMESPACE),
                        "name": portfolio.reinsurance_scope_file.filename,
                        "stored": str(portfolio.reinsurance_scope_file.file)
                    },
                    'storage_links': response.request.application_url + portfolio.get_absolute_storage_url(namespace=NAMESPACE)
                }, response.json)


class PortfolioApiCreateAnalysis(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        portfolio = fake_portfolio()

        response = self.app.get(portfolio.get_absolute_create_analysis_url(namespace=NAMESPACE), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_user_is_authenticated_object_does_not_exist___response_is_404(self):
        user = fake_user()
        portfolio = fake_portfolio()

        response = self.app.post(
            reverse(f'{NAMESPACE}:portfolio-create-analysis', kwargs={'pk': portfolio.pk + 1}),
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
            portfolio.get_absolute_create_analysis_url(namespace=NAMESPACE),
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
            portfolio.get_absolute_create_analysis_url(namespace=NAMESPACE),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({'name': 'name', 'model': model.pk}),
            content_type='application/json',
        )

        self.assertEqual(400, response.status_code)
        self.assertIn('either "location_file" or "accounts_file" must not be null', response.json['portfolio'])

    def test_model_is_not_provided___response_is_400(self):
        user = fake_user()
        portfolio = fake_portfolio()

        response = self.app.post(
            portfolio.get_absolute_create_analysis_url(namespace=NAMESPACE),
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
            portfolio.get_absolute_create_analysis_url(namespace=NAMESPACE),
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
            portfolio.get_absolute_create_analysis_url(namespace=NAMESPACE),
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
                    model.run_mode = model.run_mode_choices.V1
                    model.save()
                    portfolio = fake_portfolio(location_file=fake_related_file())

                    response = self.app.post(
                        portfolio.get_absolute_create_analysis_url(namespace=NAMESPACE),
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

                    ANALYSES_NAMESPACE = 'v1-analyses'
                    response = self.app.get(
                        analysis.get_absolute_url(namespace=ANALYSES_NAMESPACE),
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
                    self.assertEqual(response.json['settings_file'], response.request.application_url +
                                     analysis.get_absolute_settings_file_url(namespace=ANALYSES_NAMESPACE))
                    self.assertEqual(response.json['input_file'], response.request.application_url +
                                     analysis.get_absolute_input_file_url(namespace=ANALYSES_NAMESPACE))
                    self.assertEqual(response.json['lookup_errors_file'], response.request.application_url +
                                     analysis.get_absolute_lookup_errors_file_url(namespace=ANALYSES_NAMESPACE))
                    self.assertEqual(response.json['lookup_success_file'], response.request.application_url +
                                     analysis.get_absolute_lookup_success_file_url(namespace=ANALYSES_NAMESPACE))
                    self.assertEqual(response.json['lookup_validation_file'], response.request.application_url +
                                     analysis.get_absolute_lookup_validation_file_url(namespace=ANALYSES_NAMESPACE))
                    self.assertEqual(response.json['input_generation_traceback_file'], response.request.application_url +
                                     analysis.get_absolute_input_generation_traceback_file_url(namespace=ANALYSES_NAMESPACE))
                    self.assertEqual(response.json['output_file'], response.request.application_url +
                                     analysis.get_absolute_output_file_url(namespace=ANALYSES_NAMESPACE))
                    self.assertEqual(response.json['run_traceback_file'], response.request.application_url +
                                     analysis.get_absolute_run_traceback_file_url(namespace=ANALYSES_NAMESPACE))
                    generate_mock.assert_called_once_with(analysis, user, run_mode_override='V1')


class PortfolioAccountsFile(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        portfolio = fake_portfolio()

        response = self.app.get(portfolio.get_absolute_accounts_file_url(namespace=NAMESPACE), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_accounts_file_is_not_present___get_response_is_404(self):
        user = fake_user()
        portfolio = fake_portfolio()

        response = self.app.get(
            portfolio.get_absolute_accounts_file_url(namespace=NAMESPACE),
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
            portfolio.get_absolute_accounts_file_url(namespace=NAMESPACE),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_accounts_file_is_not_a_valid_format___response_is_400(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                response = self.app.post(
                    portfolio.get_absolute_accounts_file_url(namespace=NAMESPACE),
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
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_PARQUET_STORAGE=False, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                self.app.post(
                    portfolio.get_absolute_accounts_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                )

                response = self.app.get(
                    portfolio.get_absolute_accounts_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(response.body, file_content)
                self.assertEqual(response.content_type, content_type)

    def test_accounts_file_invalid_uploaded___parquet_exception_raised(self):
        content_type = 'text/csv'
        file_content = b'\xf2hb\xca\xd2\xe6\xf3\xb0\xc1\xc7'

        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_PARQUET_STORAGE=True, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                response = self.app.post(
                    portfolio.get_absolute_accounts_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                    expect_errors=True
                )
                self.assertEqual(400, response.status_code)

    def test_accounts_file_is_uploaded_as_parquet___file_can_be_retrieved(self):
        content_type = 'text/csv'
        test_data = pd.DataFrame.from_dict({"A": [1, 2, 3], "B": [4, 5, 6]})
        file_content = test_data.to_csv(index=False).encode('utf-8')

        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_PARQUET_STORAGE=True, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                self.app.post(
                    portfolio.get_absolute_accounts_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                )

                csv_response = self.app.get(
                    portfolio.get_absolute_accounts_file_url(namespace=NAMESPACE) + '?file_format=csv',
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                parquet_response = self.app.get(
                    portfolio.get_absolute_accounts_file_url(namespace=NAMESPACE) + '?file_format=parquet',
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                csv_obj = io.StringIO(csv_response.text)
                prq_obj = io.BytesIO(parquet_response.content)
                setattr(prq_obj, 'name', 'account.parquet')

                input_data = OedExposure(account=test_data)
                return_csv = OedExposure(account=csv_obj)
                return_prq = OedExposure(account=prq_obj)

                pd.testing.assert_frame_equal(
                    return_csv.account.dataframe,
                    input_data.account.dataframe)
                pd.testing.assert_frame_equal(
                    return_prq.account.dataframe,
                    input_data.account.dataframe)


class PortfolioLocationFile(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        portfolio = fake_portfolio()

        response = self.app.get(portfolio.get_absolute_location_file_url(namespace=NAMESPACE), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_location_file_is_not_present___get_response_is_404(self):
        user = fake_user()
        portfolio = fake_portfolio()

        response = self.app.get(
            portfolio.get_absolute_location_file_url(namespace=NAMESPACE),
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
            portfolio.get_absolute_location_file_url(namespace=NAMESPACE),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_location_file_is_not_a_valid_format___response_is_400(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                response = self.app.post(
                    portfolio.get_absolute_location_file_url(namespace=NAMESPACE),
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
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_PARQUET_STORAGE=False, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                self.app.post(
                    portfolio.get_absolute_location_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                )

                response = self.app.get(
                    portfolio.get_absolute_location_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(response.body, file_content)
                self.assertEqual(response.content_type, content_type)

    def test_location_file_invalid_uploaded___parquet_exception_raised(self):
        content_type = 'text/csv'
        file_content = b'\xf2hb\xca\xd2\xe6\xf3\xb0\xc1\xc7'

        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_PARQUET_STORAGE=True, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                response = self.app.post(
                    portfolio.get_absolute_location_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                    expect_errors=True
                )
                self.assertEqual(400, response.status_code)

    def test_location_file_is_uploaded_as_parquet___file_can_be_retrieved(self):
        content_type = 'text/csv'
        test_data = pd.DataFrame.from_dict({"A": [1, 2, 3], "B": [4, 5, 6]})
        file_content = test_data.to_csv(index=False).encode('utf-8')

        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_PARQUET_STORAGE=True, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                self.app.post(
                    portfolio.get_absolute_location_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                )

                csv_response = self.app.get(
                    portfolio.get_absolute_location_file_url(namespace=NAMESPACE) + '?file_format=csv',
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )
                parquet_response = self.app.get(
                    portfolio.get_absolute_location_file_url(namespace=NAMESPACE) + '?file_format=parquet',
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                csv_obj = io.StringIO(csv_response.text)
                prq_obj = io.BytesIO(parquet_response.content)
                setattr(prq_obj, 'name', 'location.parquet')

                input_data = OedExposure(location=test_data)
                return_csv = OedExposure(location=csv_obj)
                return_prq = OedExposure(location=prq_obj)

                pd.testing.assert_frame_equal(
                    return_csv.location.dataframe,
                    input_data.location.dataframe)
                pd.testing.assert_frame_equal(
                    return_prq.location.dataframe,
                    input_data.location.dataframe)


class PortfolioReinsuranceSourceFile(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        portfolio = fake_portfolio()

        response = self.app.get(portfolio.get_absolute_reinsurance_scope_file_url(namespace=NAMESPACE), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_reinsurance_scope_file_is_not_present___get_response_is_404(self):
        user = fake_user()
        portfolio = fake_portfolio()

        response = self.app.get(
            portfolio.get_absolute_reinsurance_scope_file_url(namespace=NAMESPACE),
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
            portfolio.get_absolute_reinsurance_scope_file_url(namespace=NAMESPACE),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_reinsurance_scope_file_is_not_a_valid_format___response_is_400(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                response = self.app.post(
                    portfolio.get_absolute_reinsurance_scope_file_url(namespace=NAMESPACE),
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
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_PARQUET_STORAGE=False, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                self.app.post(
                    portfolio.get_absolute_reinsurance_scope_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                )

                response = self.app.get(
                    portfolio.get_absolute_reinsurance_scope_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(response.body, file_content)
                self.assertEqual(response.content_type, content_type)

    def test_reinsurance_scope_file_invalid_uploaded___parquet_exception_raised(self):
        content_type = 'text/csv'
        file_content = b'\xf2hb\xca\xd2\xe6\xf3\xb0\xc1\xc7'

        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_PARQUET_STORAGE=True, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                response = self.app.post(
                    portfolio.get_absolute_reinsurance_scope_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                    expect_errors=True
                )
                self.assertEqual(400, response.status_code)

    def test_reinsurance_scope_file_is_uploaded_as_parquet___file_can_be_retrieved(self):
        content_type = 'text/csv'
        test_data = pd.DataFrame.from_dict({"A": [1, 2, 3], "B": [4, 5, 6]})
        file_content = test_data.to_csv(index=False).encode('utf-8')

        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_PARQUET_STORAGE=True, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                self.app.post(
                    portfolio.get_absolute_reinsurance_scope_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                )

                csv_response = self.app.get(
                    portfolio.get_absolute_reinsurance_scope_file_url(namespace=NAMESPACE) + '?file_format=csv',
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                parquet_response = self.app.get(
                    portfolio.get_absolute_reinsurance_scope_file_url(namespace=NAMESPACE) + '?file_format=parquet',
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                csv_obj = io.StringIO(csv_response.text)
                prq_obj = io.BytesIO(parquet_response.content)
                setattr(prq_obj, 'name', 'ri_scope.parquet')

                input_data = OedExposure(ri_scope=test_data)
                return_csv = OedExposure(ri_scope=csv_obj)
                return_prq = OedExposure(ri_scope=prq_obj)

                pd.testing.assert_frame_equal(
                    return_csv.ri_scope.dataframe,
                    input_data.ri_scope.dataframe)
                pd.testing.assert_frame_equal(
                    return_prq.ri_scope.dataframe,
                    input_data.ri_scope.dataframe)


class PortfolioReinsuranceInfoFile(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        portfolio = fake_portfolio()

        response = self.app.get(portfolio.get_absolute_reinsurance_info_file_url(namespace=NAMESPACE), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

    def test_reinsurance_info_file_is_not_present___get_response_is_404(self):
        user = fake_user()
        portfolio = fake_portfolio()

        response = self.app.get(
            portfolio.get_absolute_reinsurance_info_file_url(namespace=NAMESPACE),
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
            portfolio.get_absolute_reinsurance_info_file_url(namespace=NAMESPACE),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_reinsurance_info_file_is_not_a_valid_format___response_is_400(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                response = self.app.post(
                    portfolio.get_absolute_reinsurance_info_file_url(namespace=NAMESPACE),
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
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_PARQUET_STORAGE=False, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                self.app.post(
                    portfolio.get_absolute_reinsurance_info_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                )

                response = self.app.get(
                    portfolio.get_absolute_reinsurance_info_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                self.assertEqual(response.body, file_content)
                self.assertEqual(response.content_type, content_type)

    def test_reinsurance_info_file_invalid_uploaded___parquet_exception_raised(self):
        content_type = 'text/csv'
        file_content = b'\xf2hb\xca\xd2\xe6\xf3\xb0\xc1\xc7'

        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_PARQUET_STORAGE=True, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                response = self.app.post(
                    portfolio.get_absolute_reinsurance_info_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                    expect_errors=True
                )
                self.assertEqual(400, response.status_code)

    def test_reinsurance_info_file_is_uploaded_as_parquet___file_can_be_retrieved(self):
        content_type = 'text/csv'
        test_data = pd.DataFrame.from_dict({"A": [1, 2, 3], "B": [4, 5, 6]})
        file_content = test_data.to_csv(index=False).encode('utf-8')

        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_PARQUET_STORAGE=True, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                self.app.post(
                    portfolio.get_absolute_reinsurance_info_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                )

                csv_response = self.app.get(
                    portfolio.get_absolute_reinsurance_info_file_url(namespace=NAMESPACE) + '?file_format=csv',
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                parquet_response = self.app.get(
                    portfolio.get_absolute_reinsurance_info_file_url(namespace=NAMESPACE) + '?file_format=parquet',
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                csv_obj = io.StringIO(csv_response.text)
                prq_obj = io.BytesIO(parquet_response.content)
                setattr(prq_obj, 'name', 'ri_info.parquet')

                input_data = OedExposure(ri_info=test_data)
                return_csv = OedExposure(ri_info=csv_obj)
                return_prq = OedExposure(ri_info=prq_obj)

                pd.testing.assert_frame_equal(
                    return_csv.ri_info.dataframe,
                    input_data.ri_info.dataframe)
                pd.testing.assert_frame_equal(
                    return_prq.ri_info.dataframe,
                    input_data.ri_info.dataframe)


LOCATION_DATA_VALID = """PortNumber,AccNumber,LocNumber,IsTenant,BuildingID,CountryCode,Latitude,Longitude,StreetAddress,PostalCode,OccupancyCode,ConstructionCode,LocPerilsCovered,BuildingTIV,OtherTIV,ContentsTIV,BITIV,LocCurrency,OEDVersion
1,A11111,10002082046,1,1,GB,52.76698052,-0.895469856,1 ABINGDON ROAD,LE13 0HL,1050,5000,WW1,220000,0,0,0,GBP,2.0.0
1,A11111,10002082047,1,1,GB,52.76697956,-0.89536613,2 ABINGDON ROAD,LE13 0HL,1050,5000,WW1,790000,0,0,0,GBP,2.0.0
1,A11111,10002082048,1,1,GB,52.76697845,-0.895247587,3 ABINGDON ROAD,LE13 0HL,1050,5000,WW1,160000,0,0,0,GBP,2.0.0
1,A11111,10002082049,1,1,GB,52.76696096,-0.895473908,4 ABINGDON ROAD,LE13 0HL,1050,5000,WW1,30000,0,0,0,GBP,2.0.0
"""

ACCOUNT_DATA_VALID = """PortNumber,AccNumber,AccCurrency,PolNumber,PolPerilsCovered,PolInceptionDate,PolExpiryDate,LayerNumber,LayerParticipation,LayerLimit,LayerAttachment,OEDVersion
1,A11111,GBP,Layer1,WW1,2018-01-01,2018-12-31,1,0.3,5000000,500000,2.0.0
1,A11111,GBP,Layer2,WW1,2018-01-01,2018-12-31,2,0.3,100000000,5500000,2.0.0
"""

INFO_DATA_VALID = """ReinsNumber,ReinsLayerNumber,ReinsName,ReinsPeril,ReinsInceptionDate,ReinsExpiryDate,CededPercent,RiskLimit,RiskAttachment,OccLimit,OccAttachment,PlacedPercent,ReinsCurrency,InuringPriority,ReinsType,RiskLevel,UseReinsDates,OEDVersion
1,1,ABC QS,WW1,2018-01-01,2018-12-31,1,0,0,0,0,1,GBP,1,SS,LOC,N,2.0.0
"""

SCOPE_DATA_VALID = """ReinsNumber,PortNumber,AccNumber,PolNumber,LocGroup,LocNumber,CedantName,ProducerName,LOB,CountryCode,ReinsTag,CededPercent,OEDVersion
1,1,A11111,,,10002082047,,,,GB,,0.1,2.0.0
1,1,A11111,,,10002082048,,,,GB,,0.2,2.0.0
"""

LOCATION_DATA_INVALID = """Port,AccNumber,LocNumb,IsTenant,BuildingID,CountryCode,Latitude,Longitude,Street,PostalCode,OccupancyCode,ConstructionCode,LocPerilsCovered,BuildingTIV,OtherTIV,ContentsTIV,BITIV,LocCurrency,OEDVersion
1,A11111,10002082046,1,1,GB,52.76698052,-0.895469856,1 ABINGDON ROAD,LE13 0HL,1050,5000,WW1,220000,0,0,0,GBP,2.0.0
1,A11111,10002082047,1,1,GB,52.76697956,-0.89536613,2 ABINGDON ROAD,LE13 0HL,1050,5000,XXYA,790000,0,0,0,GBP,2.0.0
1,A11111,10002082048,1,1,GB,52.76697845,,3 ABINGDON ROAD,LE13 0HL,1050,5000,WW1,160000,0,0,0,GBP,2.0.0
1,A11111,10002082049,1,1,GB,52.76696096,-0.895473908,4 ABINGDON ROAD,LE13 0HL,1050,-1,WW1,30000,0,0,0,GBP,2.0.0
"""


class PortfolioValidation(WebTestMixin, TestCase):
    # Testing for the functionality moved into test_server_tasks
    @patch('src.server.oasisapi.portfolios.models.Portfolio.run_oed_validation_signature')
    def test_validation_celery_call(self, mock_signature):
        content_type = 'text/csv'
        test_data = pd.read_csv(io.StringIO(LOCATION_DATA_VALID))
        file_content = test_data.to_csv(index=False).encode('utf-8')

        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                self.app.post(
                    portfolio.get_absolute_reinsurance_scope_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                )

                validate_response = self.app.get(
                    portfolio.get_absolute_url(namespace=NAMESPACE) + 'validate/',
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                # Get current validate status - Not yet run
                self.assertEqual(200, validate_response.status_code)
                self.assertEqual(validate_response.json, {
                    'location_validated': None,
                    'accounts_validated': None,
                    'reinsurance_info_validated': None,
                    'reinsurance_scope_validated': False})

                # Run validate - check is valid
                validate_response = self.app.post(
                    portfolio.get_absolute_url(namespace=NAMESPACE) + 'validate/',
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    expect_errors=True,
                )
                mock_signature.assert_called_once()

    def test_all_exposure__are_valid_setup(self):
        content_type = 'text/csv'
        loc_data = pd.read_csv(io.StringIO(LOCATION_DATA_VALID))
        acc_data = pd.read_csv(io.StringIO(ACCOUNT_DATA_VALID))
        inf_data = pd.read_csv(io.StringIO(INFO_DATA_VALID))
        scp_data = pd.read_csv(io.StringIO(SCOPE_DATA_VALID))

        loc_file_content = loc_data.to_csv(index=False).encode('utf-8')
        acc_file_content = acc_data.to_csv(index=False).encode('utf-8')
        inf_file_content = inf_data.to_csv(index=False).encode('utf-8')
        scp_file_content = scp_data.to_csv(index=False).encode('utf-8')

        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                self.app.post(
                    portfolio.get_absolute_location_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), loc_file_content),
                    ),
                )
                self.app.post(
                    portfolio.get_absolute_accounts_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), acc_file_content),
                    ),
                )
                self.app.post(
                    portfolio.get_absolute_reinsurance_info_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), inf_file_content),
                    ),
                )
                self.app.post(
                    portfolio.get_absolute_reinsurance_scope_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), scp_file_content),
                    ),
                )

                validate_response = self.app.get(
                    portfolio.get_absolute_url(namespace=NAMESPACE) + 'validate/',
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                # Get current validate status - Not yet run
                self.assertEqual(200, validate_response.status_code)
                self.assertEqual(validate_response.json, {
                    'location_validated': False,
                    'accounts_validated': False,
                    'reinsurance_info_validated': False,
                    'reinsurance_scope_validated': False})

    def test_location_file__is_valid_setup(self):
        content_type = 'text/csv'
        test_data = pd.read_csv(io.StringIO(LOCATION_DATA_VALID))
        file_content = test_data.to_csv(index=False).encode('utf-8')

        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                self.app.post(
                    portfolio.get_absolute_location_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                )

                validate_response = self.app.get(
                    portfolio.get_absolute_url(namespace=NAMESPACE) + 'validate/',
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                # Get current validate status - Not yet run
                self.assertEqual(200, validate_response.status_code)
                self.assertEqual(validate_response.json, {
                    'location_validated': False,
                    'accounts_validated': None,
                    'reinsurance_info_validated': None,
                    'reinsurance_scope_validated': None})

    def test_location_file__is_invalid_setup(self):
        content_type = 'text/csv'
        test_data = pd.read_csv(io.StringIO(LOCATION_DATA_INVALID))
        file_content = test_data.to_csv(index=False).encode('utf-8')

        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                self.app.post(
                    portfolio.get_absolute_location_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                )
                validate_response = self.app.get(
                    portfolio.get_absolute_url(namespace=NAMESPACE) + 'validate/',
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                # Get current validate status - Not yet run
                self.assertEqual(200, validate_response.status_code)
                self.assertEqual(validate_response.json, {
                    'location_validated': False,
                    'accounts_validated': None,
                    'reinsurance_info_validated': None,
                    'reinsurance_scope_validated': None})

    def test_account_file__is_invalid_setup(self):
        content_type = 'text/csv'
        test_data = pd.read_csv(io.StringIO(LOCATION_DATA_VALID))
        file_content = test_data.to_csv(index=False).encode('utf-8')

        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                self.app.post(
                    portfolio.get_absolute_accounts_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                )

                validate_response = self.app.get(
                    portfolio.get_absolute_url(namespace=NAMESPACE) + 'validate/',
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                # Get current validate status - Not yet run
                self.assertEqual(200, validate_response.status_code)
                self.assertEqual(validate_response.json, {
                    'location_validated': None,
                    'accounts_validated': False,
                    'reinsurance_info_validated': None,
                    'reinsurance_scope_validated': None})

    def test_reinsurance_info_file__is_invalid_setup(self):
        content_type = 'text/csv'
        test_data = pd.read_csv(io.StringIO(LOCATION_DATA_VALID))
        file_content = test_data.to_csv(index=False).encode('utf-8')

        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                self.app.post(
                    portfolio.get_absolute_reinsurance_info_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                )

                validate_response = self.app.get(
                    portfolio.get_absolute_url(namespace=NAMESPACE) + 'validate/',
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                # Get current validate status - Not yet run
                self.assertEqual(200, validate_response.status_code)
                self.assertEqual(validate_response.json, {
                    'location_validated': None,
                    'accounts_validated': None,
                    'reinsurance_info_validated': False,
                    'reinsurance_scope_validated': None})

    def test_reinsurance_scope_file__is_invalid_setup(self):
        content_type = 'text/csv'
        test_data = pd.read_csv(io.StringIO(LOCATION_DATA_VALID))
        file_content = test_data.to_csv(index=False).encode('utf-8')

        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d, PORTFOLIO_UPLOAD_VALIDATION=False):
                user = fake_user()
                portfolio = fake_portfolio()

                self.app.post(
                    portfolio.get_absolute_reinsurance_scope_file_url(namespace=NAMESPACE),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    upload_files=(
                        ('file', 'file{}'.format(mimetypes.guess_extension(content_type)), file_content),
                    ),
                )

                validate_response = self.app.get(
                    portfolio.get_absolute_url(namespace=NAMESPACE) + 'validate/',
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )

                # Get current validate status - Not yet run
                self.assertEqual(200, validate_response.status_code)
                self.assertEqual(validate_response.json, {
                    'location_validated': None,
                    'accounts_validated': None,
                    'reinsurance_info_validated': None,
                    'reinsurance_scope_validated': False})
