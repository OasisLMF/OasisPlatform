import mock
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from src.server.oasisapi.analysis_models.models import AnalysisModel
from src.server.oasisapi.analysis_models.v2_api.tests.fakes import fake_analysis_model
from src.server.oasisapi.auth.tests.fakes import fake_user
from src.server.oasisapi.oidc.keycloak_auth import KeycloakOIDCAuthenticationBackend
from src.server.oasisapi.oidc.models import KeycloakUserId

SUB = 'a1b2c3d4-sub'
USERNAME = 'platform-service-controller'
CLAIMS = {'sub': SUB, 'preferred_username': USERNAME, 'groups': []}


@override_settings(
    OIDC_OP_TOKEN_ENDPOINT='http://fake-host/token',
    OIDC_OP_USER_ENDPOINT='http://fake-host/userinfo',
    OIDC_RP_CLIENT_ID='client',
    OIDC_RP_CLIENT_SECRET='secret',
)
class TestOIDCUserSync(TestCase):
    """
    Django user sync for OIDC logins, in particular concurrent first logins for the same identity (e.g. the
    worker-controller and model registration job sharing one service account).
    """

    def setUp(self):
        self.backend = KeycloakOIDCAuthenticationBackend()

    def login(self, claims=CLAIMS):
        with mock.patch.object(self.backend, 'get_userinfo', return_value=dict(claims)):
            return self.backend.get_or_create_user('access', 'id', {})

    def test_first_login_creates_user_bound_to_sub(self):
        user = self.login()

        self.assertEqual(user.username, USERNAME)
        self.assertEqual(KeycloakUserId.objects.get(user=user).keycloak_user_id, SUB)

    def test_create_user_reuses_user_created_by_concurrent_request(self):
        # The other request committed the user and its KeycloakUserId after our lookup missed it
        existing = fake_user(username=USERNAME)
        KeycloakUserId.objects.create(user=existing, keycloak_user_id=SUB)

        user = self.backend.create_user(USERNAME, dict(CLAIMS))

        self.assertEqual(user.pk, existing.pk)
        self.assertEqual(KeycloakUserId.objects.filter(keycloak_user_id=SUB).count(), 1)

    def test_lost_race_does_not_archive_or_delete_same_identity(self):
        existing = fake_user(username=USERNAME)
        KeycloakUserId.objects.create(user=existing, keycloak_user_id=SUB)
        model = fake_analysis_model(creator=existing)

        with mock.patch.object(self.backend, 'get_user_by_keycloak_id', return_value=None):
            user = self.login()

        self.assertEqual(user.pk, existing.pk)
        self.assertEqual(get_user_model().objects.get(pk=existing.pk).username, USERNAME)
        self.assertTrue(AnalysisModel.objects.filter(pk=model.pk).exists())

    def test_duplicate_sub_bindings_do_not_cascade_delete(self):
        # State left behind by the original race: an archived user and a current user both bound to the same sub.
        # Every subsequent login used to delete the archived user (and via CASCADE, its models).
        archived = fake_user(username=f'{USERNAME}-{SUB}')
        KeycloakUserId.objects.create(user=archived, keycloak_user_id=SUB)
        current = fake_user(username=USERNAME)
        KeycloakUserId.objects.create(user=current, keycloak_user_id=SUB)
        model = fake_analysis_model(creator=archived)

        for _ in range(3):
            user = self.login()
            self.assertEqual(user.pk, current.pk)

        self.assertTrue(get_user_model().objects.filter(pk=archived.pk).exists())
        self.assertTrue(AnalysisModel.objects.filter(pk=model.pk).exists())

    def test_user_with_same_username_but_other_sub_is_archived(self):
        old = fake_user(username=USERNAME)
        KeycloakUserId.objects.create(user=old, keycloak_user_id='old-sub')
        model = fake_analysis_model(creator=old)

        user = self.login()

        self.assertNotEqual(user.pk, old.pk)
        self.assertEqual(user.username, USERNAME)
        self.assertEqual(get_user_model().objects.get(pk=old.pk).username, f'{USERNAME}-{SUB}')
        self.assertTrue(AnalysisModel.objects.filter(pk=model.pk).exists())
