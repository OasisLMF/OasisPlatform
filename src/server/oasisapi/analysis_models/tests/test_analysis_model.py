import json
import string

from backports.tempfile import TemporaryDirectory
from django.test import override_settings
from django.urls import reverse
from django_webtest import WebTest, WebTestMixin
from hypothesis import given, settings
from hypothesis.extra.django import TestCase
from hypothesis.strategies import text
from rest_framework_simplejwt.tokens import AccessToken

from ...auth.tests.fakes import fake_user
from ..models import AnalysisModel

from .fakes import fake_analysis_model

# Override default deadline for all tests to 8s
settings.register_profile("ci", deadline=800.0)
settings.load_profile("ci")


class AnalysisModelApi(WebTest, TestCase):
    @given(
        supplier_id=text(alphabet=string.ascii_letters, min_size=1, max_size=10),
        version_id=text(alphabet=string.whitespace, min_size=0, max_size=10),
    )
    def test_version_id_is_missing___response_is_400(self, supplier_id, version_id):
        user = fake_user()

        response = self.app.post(
            reverse('analysis-model-list', kwargs={'version': 'v1'}),
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
            reverse('analysis-model-list', kwargs={'version': 'v1'}),
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
    def test_data_is_valid___object_is_created(self, supplier_id, model_id, version_id):
        user = fake_user()

        response = self.app.post(
            reverse('analysis-model-list', kwargs={'version': 'v1'}),
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



class ModelSettingsJson(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        models = fake_analysis_model()

        response = self.app.get(models.get_absolute_settings_url(), expect_errors=True)
        self.assertIn(response.status_code, [401,403])

    def test_settings_json_is_not_present___get_response_is_404(self):
        user = fake_user()
        models = fake_analysis_model()

        response = self.app.get(
            models.get_absolute_settings_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_settings_json_is_not_present___delete_response_is_404(self):
        user = fake_user()
        models = fake_analysis_model()

        response = self.app.delete(
            models.get_absolute_settings_url(),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            expect_errors=True,
        )

        self.assertEqual(404, response.status_code)

    def test_settings_json_is_not_valid___response_is_400(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                models = fake_analysis_model()
                json_data = {
                    "model_settings":[
                        {
                            "event_set":{
                                "name": "Event Set",
                                "desc": "Either Probablistic or Historic",
                                "type": "boolean",
                                "default": "P",
                                "values":{
                                    "P": "Proabilistic",
                                    "H": "Historic"
                                }
                             }
                         },
                    ],
                    "Invalid_section": 'Null',
                    "lookup_settings":[
                        {
                            "PerilCodes":{
                                "type":"dictionary",
                                "values":{
                                    "WSSS": "Single Peril: Storm Surge",
                                    "WTC": 1,
                                }
                            }
                        }
                    ]
                }

                response = self.app.post(
                    models.get_absolute_settings_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    params=json.dumps(json_data),
                    content_type='application/json',
                    expect_errors=True,
                )

                validation_error =  {
                    'model_settings-0-event_set-type': "'boolean' is not one of ['dictionary']", 
                    'lookup_settings-0-PerilCodes-values-WTC': "1 is not of type 'string'", 
                    'lookup_settings-0-PerilCodes-values': "'WSSS' does not match any of the regexes: '^[a-zA-Z0-9]{3}$'"
                }
                self.assertEqual(400, response.status_code)
                self.assertEqual(json.loads(response.body), validation_error)


    def test_settings_json_is_uploaded___can_be_retrieved(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                models = fake_analysis_model()
                json_data = {
                    "model_settings":[
                        {
                            "event_set":{
                                "name": "Event Set",
                                "desc": "Either Probablistic or Historic",
                                "type":"dictionary",
                                "default": "P",
                                "values":{
                                    "P": "Proabilistic",
                                    "H": "Historic"
                                }
                             }
                         },
                         {
                            "event_occurrence_id":{
                                "name": "Occurrence Set",
                                "desc": "PiWind Occurrence selection",
                                "type":"dictionary",
                                "default": "1",
                                "values":{
                                   "1":"Long Term"
                                }
                            }

                         }
                    ],
                    "lookup_settings":[
                        {
                            "PerilCodes":{
                                "type":"dictionary",
                                "values":{
                                    "WSS": "Single Peril: Storm Surge",
                                    "WTC": "Single Peril: Tropical Cyclone",
                                    "WW1": "Group Peril: Windstorm with storm surge",
                                    "WW2": "Group Peril: Windstorm w/o storm surge"
                                }
                            }
                        }
                    ]
                }

                self.app.post(
                    models.get_absolute_settings_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                    params=json.dumps(json_data),
                    content_type='application/json'
                )

                response = self.app.get(
                    models.get_absolute_settings_url(),
                    headers={
                        'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                    },
                )
                self.assertEqual(json.loads(response.body), json_data)
                self.assertEqual(response.content_type, 'application/json')
