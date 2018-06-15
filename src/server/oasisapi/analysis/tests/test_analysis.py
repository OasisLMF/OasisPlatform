import json
import string

from backports.tempfile import TemporaryDirectory
from django.test import override_settings
from django.urls import reverse
from django_webtest import WebTestMixin
from hypothesis import given
from hypothesis.extra.django import TestCase
from hypothesis.strategies import text, binary
from rest_framework_simplejwt.tokens import AccessToken

from ...portfolio.tests.fakes import fake_portfolio
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
            'id': analysis.pk,
            'portfolio': portfolio.pk,
            'name': name,
            'created': analysis.created.strftime('%y-%m-%dT%H:%M:%S.%f%z'),
            'modified': analysis.modified.strftime('%y-%m-%dT%H:%M:%S.%f%z'),
            'settings_file': None,
            'input_file': None,
            'input_errors_file': None,
            'output_file': None,
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

                self.assertEqual(analysis.input_file.read(), file_content)
                self.assertEqual(response.json['input_file'], response.request.application_url + analysis.input_file.url)
