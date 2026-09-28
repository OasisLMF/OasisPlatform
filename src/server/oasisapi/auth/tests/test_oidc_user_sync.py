import mock
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.test import TestCase, override_settings

from src.server.oasisapi.analysis_models.models import AnalysisModel
from src.server.oasisapi.analysis_models.v2_api.tests.fakes import fake_analysis_model
from src.server.oasisapi.auth.tests.fakes import add_fake_group, fake_user
from src.server.oasisapi.oidc.generic_auth import GenericOIDCAuthenticationBackend
from src.server.oasisapi.oidc.models import OIDCUserId

SUB = 'a1b2c3d4-sub'
USERNAME = 'platform-service-controller'
CLAIMS = {'sub': SUB, 'preferred_username': USERNAME, 'is_service_account': True}


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
        self.backend = GenericOIDCAuthenticationBackend()

    def login(self, claims=CLAIMS):
        with mock.patch.object(self.backend, 'get_userinfo', return_value=dict(claims)):
            return self.backend.get_or_create_user('access', 'id', {})

    def test_first_login_creates_user_bound_to_sub(self):
        user = self.login()

        self.assertEqual(user.username, USERNAME)
        self.assertEqual(OIDCUserId.objects.get(user=user).oidc_sub, SUB)

    def test_create_user_reuses_user_created_by_concurrent_request(self):
        # The other request committed the user and its OIDCUserId after our lookup missed it
        existing = fake_user(username=USERNAME)
        OIDCUserId.objects.create(user=existing, oidc_sub=SUB)

        user = self.backend.create_user(USERNAME, dict(CLAIMS))

        self.assertEqual(user.pk, existing.pk)
        self.assertEqual(OIDCUserId.objects.filter(oidc_sub=SUB).count(), 1)

    def test_lost_race_does_not_archive_or_delete_same_identity(self):
        existing = fake_user(username=USERNAME)
        OIDCUserId.objects.create(user=existing, oidc_sub=SUB)
        model = fake_analysis_model(creator=existing)

        with mock.patch.object(self.backend, 'get_user_by_oidc_id', return_value=None):
            user = self.login()

        self.assertEqual(user.pk, existing.pk)
        self.assertEqual(get_user_model().objects.get(pk=existing.pk).username, USERNAME)
        self.assertTrue(AnalysisModel.objects.filter(pk=model.pk).exists())

    def test_duplicate_sub_bindings_do_not_cascade_delete(self):
        # State left behind by the original race: an archived user and a current user both bound to the same sub.
        # Every subsequent login used to delete the archived user (and via CASCADE, its models).
        archived = fake_user(username=f'{USERNAME}-{SUB}')
        OIDCUserId.objects.create(user=archived, oidc_sub=SUB)
        current = fake_user(username=USERNAME)
        OIDCUserId.objects.create(user=current, oidc_sub=SUB)
        model = fake_analysis_model(creator=archived)

        for _ in range(3):
            user = self.login()
            self.assertEqual(user.pk, current.pk)

        self.assertTrue(get_user_model().objects.filter(pk=archived.pk).exists())
        self.assertTrue(AnalysisModel.objects.filter(pk=model.pk).exists())

    def test_integrity_error_retries_in_fresh_transaction(self):
        # e.g. under REPEATABLE READ, where get_or_create's own retry can't see the winner's user
        existing = fake_user(username=USERNAME)

        with mock.patch.object(self.backend, 'get_user_by_oidc_id', side_effect=[None, existing]), \
                mock.patch.object(self.backend, 'create_user', side_effect=IntegrityError) as create_user:
            user = self.login()

        self.assertEqual(user.pk, existing.pk)
        self.assertEqual(create_user.call_count, 1)

    def test_repeated_integrity_error_is_raised(self):
        with mock.patch.object(self.backend, 'create_user', side_effect=IntegrityError) as create_user:
            with self.assertRaises(IntegrityError):
                self.login()

        self.assertEqual(create_user.call_count, 2)

    def test_lost_race_to_other_identity_is_rejected(self):
        # Another identity created the username after our archive step missed it, so get_or_create hands us its user
        other = fake_user(username=USERNAME, is_superuser=False, is_staff=False)
        OIDCUserId.objects.create(user=other, oidc_sub='other-sub')
        add_fake_group(other, 'other-group')

        with mock.patch.object(self.backend, 'archive_old_user'):
            with self.assertRaises(PermissionDenied):
                self.login(dict(CLAIMS, groups=['admin']))

        other.refresh_from_db()
        self.assertEqual(other.username, USERNAME)
        self.assertFalse(other.is_superuser)
        self.assertEqual([g.name for g in other.groups.all()], ['other-group'])
        self.assertEqual(OIDCUserId.objects.get(user=other).oidc_sub, 'other-sub')

    def test_user_with_same_username_but_other_sub_is_archived(self):
        old = fake_user(username=USERNAME)
        OIDCUserId.objects.create(user=old, oidc_sub='old-sub')
        model = fake_analysis_model(creator=old)

        user = self.login()

        self.assertNotEqual(user.pk, old.pk)
        self.assertEqual(user.username, USERNAME)
        archived = get_user_model().objects.get(pk=old.pk)
        self.assertEqual(archived.username, f'{USERNAME}-{SUB}')
        self.assertFalse(archived.is_active)
        self.assertTrue(AnalysisModel.objects.filter(pk=model.pk).exists())
