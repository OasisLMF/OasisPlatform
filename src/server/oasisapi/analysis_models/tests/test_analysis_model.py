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


    """ Add these check back in once models auto-update their settings fields
    """
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
                    "model_settings":{
                        "event_set":{
                            "name": "Event Set",
                            "default": "P",
                            "options":[
                                {"id":"P", "desc": "Proabilistic"},
                                {"id":"H", "desc": "Historic"}
                            ]
                         },
                        "event_occurrence_id":{
                            "name": "Occurrence Set",
                            "desc": "PiWind Occurrence selection",
                            "default": 1,
                            "options":[
                                {"id":"1", "desc": "Long Term"}
                            ]
                        },
                        "boolean_parameters": [
                            {"name": "peril_wind", "desc":"Boolean option", "default": 1.1},
                            {"name": "peril_surge", "desc":"Boolean option", "default": True}
                        ],
                        "float_parameter": [
                            {"name": "float_1", "desc":"Some float value", "default": False, "max":1.0, "min":0.0},
                            {"name": "float_2", "desc":"Some float value", "default": 0.3, "max":1.0, "min":0.0}
                        ]
                     },
                    "lookup_settings":{
                        "supported_perils":[
                           {"i": "WSS", "desc": "Single Peril: Storm Surge"},
                           {"id": "WTC", "des": "Single Peril: Tropical Cyclone"},
                           {"id": "WW11", "desc": "Group Peril: Windstorm with storm surge"},
                           {"id": "WW2", "desc": "Group Peril: Windstorm w/o storm surge"}
                        ]
                    }
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
                    'model_settings': ["Additional properties are not allowed ('float_parameter' was unexpected)"], 
                    'model_settings-event_set': ["'desc' is a required property"],
                    'model_settings-event_occurrence_id-default': ["1 is not of type 'string'"],
                    'model_settings-boolean_parameters-0-default': ["1.1 is not of type 'boolean'"],
                    'lookup_settings-supported_perils-0': ["Additional properties are not allowed ('i' was unexpected)", "'id' is a required property"],
                    'lookup_settings-supported_perils-1': ["Additional properties are not allowed ('des' was unexpected)", "'desc' is a required property"],
                    'lookup_settings-supported_perils-2-id': ["'WW11' is too long"]
                }

                self.assertEqual(400, response.status_code)
                self.assertDictEqual.__self__.maxDiff = None
                self.assertDictEqual(json.loads(response.body), validation_error)


    def test_settings_json_is_uploaded___can_be_retrieved(self):
        with TemporaryDirectory() as d:
            with override_settings(MEDIA_ROOT=d):
                user = fake_user()
                models = fake_analysis_model()
                json_data = {
                    "model_settings":{
                        "event_set":{
                            "name": "Event Set",
                            "desc": "Either Probablistic or Historic",
                            "default": "P",
                            "options":[
                                {"id":"P", "desc": "Proabilistic"},
                                {"id":"H", "desc": "Historic"}
                            ]
                         },
                        "event_occurrence_id":{
                            "name": "Occurrence Set",
                            "desc": "PiWind Occurrence selection",
                            "default": "1",
                            "options":[
                                {"id":"1", "desc": "Long Term"}
                            ]
                        },
                        "boolean_parameters": [
                            {"name": "peril_wind", "desc":"Boolean option", "default": False},
                            {"name": "peril_surge", "desc":"Boolean option", "default": True}
                        ],
                        "float_parameters": [
                            {"name": "float_1", "desc":"Some float value", "default": 0.5, "max":1.0, "min":0.0},
                            {"name": "float_2", "desc":"Some float value", "default": 0.3, "max":1.0, "min":0.0}
                        ]
                     },
                    "lookup_settings":{
                        "supported_perils":[
                           {"id": "WSS", "desc": "Single Peril: Storm Surge"},
                           {"id": "WTC", "desc": "Single Peril: Tropical Cyclone"},
                           {"id": "WW1", "desc": "Group Peril: Windstorm with storm surge"},
                           {"id": "WW2", "desc": "Group Peril: Windstorm w/o storm surge"}
                        ]
                    }
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
                self.assertDictEqual.__self__.maxDiff = None
                self.assertDictEqual(json.loads(response.body), json_data)
                self.assertEqual(response.content_type, 'application/json')
