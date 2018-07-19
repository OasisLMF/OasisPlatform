import json
import string

from django.urls import reverse
from django_webtest import WebTest
from hypothesis import given, settings
from hypothesis.extra.django import TestCase
from hypothesis.strategies import text
from rest_framework_simplejwt.tokens import AccessToken

from ...auth.tests.fakes import fake_user
from ..models import AnalysisModel


class AnalysisModelApi(WebTest, TestCase):
    @given(
        supplier_id=text(alphabet=string.ascii_letters, min_size=1, max_size=10),
        version_id=text(alphabet=string.whitespace, min_size=0, max_size=10),
    )
    def test_version_id_is_missing___response_is_400(self, supplier_id, version_id):
        user = fake_user()

        response = self.app.post(
            reverse('analysis-model-list'),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({
                'supplier_id': supplier_id,
                'version_id': version_id,
            }),
            content_type='application/json',
        )

        self.assertEqual(400, response.status_code)
        self.assertFalse(AnalysisModel.objects.exists())

    @given(
        supplier_id=text(alphabet=string.whitespace, min_size=0, max_size=10),
        version_id=text(alphabet=string.ascii_letters, min_size=1, max_size=10),
    )
    def test_supplier_id_is_missing___response_is_400(self, supplier_id, version_id):
        user = fake_user()

        response = self.app.post(
            reverse('analysis-model-list'),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({
                'supplier_id': supplier_id,
                'version_id': version_id,
            }),
            content_type='application/json',
        )

        self.assertEqual(400, response.status_code)
        self.assertFalse(AnalysisModel.objects.exists())

    @given(
        supplier_id=text(alphabet=string.ascii_letters, min_size=1, max_size=10),
        model_id=text(alphabet=string.ascii_letters, min_size=1, max_size=10),
        version_id=text(alphabet=string.ascii_letters, min_size=1, max_size=10),
    )
    @settings(deadline=None)
    def test_data_is_valid___object_is_created(self, supplier_id, model_id, version_id):
        user = fake_user()

        response = self.app.post(
            reverse('analysis-model-list'),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({
                'supplier_id': supplier_id,
                'model_id': model_id,
                'version_id': version_id,
            }),
            content_type='application/json',
        )

        model = AnalysisModel.objects.first()

        self.assertEqual(201, response.status_code)
        self.assertEqual(model.supplier_id, supplier_id)
        self.assertEqual(model.version_id, version_id)
        self.assertEqual(model.model_id, model_id)
        self.assertEqual(model.version_id, version_id)
