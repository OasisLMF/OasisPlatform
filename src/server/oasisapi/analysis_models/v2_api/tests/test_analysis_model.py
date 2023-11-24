import json
import string

from backports.tempfile import TemporaryDirectory
from django.contrib.auth.models import Group
from django.test import override_settings
from django.urls import reverse
from django_webtest import WebTest, WebTestMixin
from hypothesis import given, settings
from hypothesis.extra.django import TestCase
from hypothesis.strategies import text
from rest_framework_simplejwt.tokens import AccessToken

from .fakes import fake_analysis_model
from src.server.oasisapi.analysis_models.models import AnalysisModel
from src.server.oasisapi.auth.tests.fakes import fake_user, add_fake_group

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

    @given(
        supplier_id=text(alphabet=string.ascii_letters, min_size=1, max_size=10),
        model_id=text(alphabet=string.ascii_letters, min_size=1, max_size=10),
        version_id=text(alphabet=string.ascii_letters, min_size=1, max_size=10),
        group_name=text(alphabet=string.ascii_letters, min_size=1, max_size=10),
    )
    def test_create_with_default_groups___response_is_201(self, supplier_id, model_id, version_id, group_name):
        user = fake_user()
        add_fake_group(user, group_name)

        response = self.app.post(
            reverse('analysis-model-list', kwargs={'version': 'v1'}),
            expect_errors=True,
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

        self.assertEqual(201, response.status_code)
        groups = json.loads(response.body).get('groups')
        self.assertEqual(1, len(groups))
        self.assertEqual(group_name, groups[0])
        self.assertTrue(AnalysisModel.objects.exists())

    @given(
        supplier_id=text(alphabet=string.ascii_letters, min_size=1, max_size=10),
        model_id=text(alphabet=string.ascii_letters, min_size=1, max_size=10),
        version_id=text(alphabet=string.ascii_letters, min_size=1, max_size=10),
        group_name=text(alphabet=string.ascii_letters, min_size=1, max_size=10),
    )
    def test_create_with_valid_groups___response_is_201(self, supplier_id, model_id, version_id, group_name):
        user = fake_user()
        add_fake_group(user, group_name)

        response = self.app.post(
            reverse('analysis-model-list', kwargs={'version': 'v1'}),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({
                'supplier_id': supplier_id,
                'model_id': model_id,
                'version_id': version_id,
                'groups': [group_name]
            }),
            content_type='application/json',
        )

        self.assertEqual(201, response.status_code)
        groups = json.loads(response.body).get('groups')
        self.assertEqual(1, len(groups))
        self.assertEqual(group_name, groups[0])
        self.assertTrue(AnalysisModel.objects.exists())

    @given(
        supplier_id=text(alphabet=string.ascii_letters, min_size=1, max_size=10),
        model_id=text(alphabet=string.ascii_letters, min_size=1, max_size=10),
        version_id=text(alphabet=string.ascii_letters, min_size=1, max_size=10),
    )
    def test_create_with_invalid_groups___response_is_403(self, supplier_id, model_id, version_id):
        user = fake_user()

        response = self.app.post(
            reverse('analysis-model-list', kwargs={'version': 'v1'}),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            params=json.dumps({
                'supplier_id': supplier_id,
                'model_id': model_id,
                'version_id': version_id,
                'groups': ['non-existing-group']
            }),
            content_type='application/json',
        )

        self.assertEqual(400, response.status_code)

    @given(
        group_name=text(alphabet=string.ascii_letters, min_size=1, max_size=10),
    )
    def test_create_with_default_groups_and_get_with_other_groups___response_is_empty(self, group_name):
        user_with_group = fake_user()
        add_fake_group(user_with_group, group_name)
        model = AnalysisModel.objects.create(
            supplier_id='s',
            model_id='m',
            version_id='v',
            creator=user_with_group,
        )
        model.groups.add(user_with_group.groups.all()[0])

        # List models as the user that created it
        response = self.app.get(
            reverse('analysis-model-list', kwargs={'version': 'v1'}),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user_with_group))
            },
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(json.loads(response.body)))

        # Test with a user not a member of the group the model was created with
        user_without_group = fake_user()
        response = self.app.get(
            reverse('analysis-model-list', kwargs={'version': 'v1'}),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user_without_group))
            },
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(0, len(json.loads(response.body)))

    @given(
        group_name=text(alphabet=string.ascii_letters, min_size=1, max_size=10),
    )
    def test_as_admin_create_with_non_existing_groups___successfully(self, group_name):
        admin_user = fake_user()
        admin_user.is_staff = True
        admin_user.save()

        response = self.app.post(
            reverse('analysis-model-list', kwargs={'version': 'v1'}),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(admin_user))
            },
            params=json.dumps({
                'supplier_id': 'supplier',
                'model_id': 'model',
                'version_id': 'version',
                'groups': [group_name],
            }),
            content_type='application/json',
        )
        self.assertEqual(201, response.status_code)
        groups = Group.objects.all()
        self.assertEqual(1, len(groups))

    @given(
        group_name=text(alphabet=string.ascii_letters, min_size=1, max_size=10),
    )
    def test_as_admin_create_with_non_existing_groups___successfully(self, group_name):
        ordinary_user = fake_user()

        response = self.app.post(
            reverse('analysis-model-list', kwargs={'version': 'v1'}),
            expect_errors=True,
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(ordinary_user))
            },
            params=json.dumps({
                'supplier_id': 'supplier',
                'model_id': 'model',
                'version_id': 'version',
                'groups': [group_name],
            }),
            content_type='application/json',
        )
        self.assertEqual(400, response.status_code)
        self.assertEqual({'groups': ['Object with name=' + group_name + ' does not exist.']}, json.loads(response.content))


class ModelSettingsJson(WebTestMixin, TestCase):
    def test_user_is_not_authenticated___response_is_forbidden(self):
        models = fake_analysis_model()

        response = self.app.get(models.get_absolute_settings_url(), expect_errors=True)
        self.assertIn(response.status_code, [401, 403])

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
                    "model_settings": {
                        "event_set": {
                            "name": "Event Set",
                            "default": "P",
                            "options": [
                                {"id": "P", "desc": "Proabilistic"},
                                {"id": "H", "desc": "Historic"}
                            ]
                        },
                        "event_occurrence_id": {
                            "name": "Occurrence Set",
                            "desc": "PiWind Occurrence selection",
                            "default": 1,
                            "options": [
                                {"id": "1", "desc": "Long Term"}
                            ]
                        },
                        "boolean_parameters": [
                            {"name": "peril_wind", "desc": "Boolean option", "default": 1.1},
                            {"name": "peril_surge", "desc": "Boolean option", "default": True}
                        ],
                        "float_parameter": [
                            {"name": "float_1", "desc": "Some float value", "default": False, "max": 1.0, "min": 0.0},
                            {"name": "float_2", "desc": "Some float value", "default": 0.3, "max": 1.0, "min": 0.0}
                        ]
                    },
                    "lookup_settings": {
                        "supported_perils": [
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

                validation_error = {
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
                    "model_settings": {
                        "event_set": {
                            "name": "Event Set",
                            "desc": "Either Probablistic or Historic",
                            "default": "P",
                            "options": [
                                {"id": "P", "desc": "Proabilistic"},
                                {"id": "H", "desc": "Historic"}
                            ]
                        },
                        "event_occurrence_id": {
                            "name": "Occurrence Set",
                            "desc": "PiWind Occurrence selection",
                            "default": "1",
                            "options": [
                                {"id": "1", "desc": "Long Term"}
                            ]
                        },
                        "boolean_parameters": [
                            {"name": "peril_wind", "desc": "Boolean option", "default": False},
                            {"name": "peril_surge", "desc": "Boolean option", "default": True}
                        ],
                        "float_parameters": [
                            {"name": "float_1", "desc": "Some float value", "default": 0.5, "max": 1.0, "min": 0.0},
                            {"name": "float_2", "desc": "Some float value", "default": 0.3, "max": 1.0, "min": 0.0}
                        ]
                    },
                    "lookup_settings": {
                        "supported_perils": [
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
