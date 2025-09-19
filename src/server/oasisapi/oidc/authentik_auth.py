from django.contrib.auth.models import Group
from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from mozilla_django_oidc import auth
from src.server.oasisapi.oidc.common import auth_server_create_connection
from src.server.oasisapi.oidc.models import OIDCUserId

from urllib3.util import connection


class AuthentikOIDCAuthenticationBackend(auth.OIDCAuthenticationBackend):
    """
    Extends Mozilla Django OIDC backend for Authentik.

    - Verifies JWT from Authentik
    - Creates or updates a corresponding Django user
    - Syncs groups and roles from Authentik claims
    """

    connection.create_connection = auth_server_create_connection

    def get_or_create_user(self, access_token, id_token, payload):
        user_info = self.get_userinfo(access_token, id_token, payload)
        is_service_account = user_info.get("is_service_account", False)

        sub = self.get_userinfo_attribute(user_info, 'sub')
        username = user_info.get("preferred_username", None)
        if not username and is_service_account:
            username = "tmp-service-account-username"
        elif not username:
            raise SuspiciousOperation('Required key not found in claim: preferred_username')

        user = self.get_user_by_oidc_id(sub)

        if user:
            return self.update_user(user, username, user_info)
        else:
            self.archive_old_user(username, sub)
            return self.create_user(username, user_info)

    def create_user(self, username, claims):
        user = self.UserModel.objects.create_user(username)
        self.update_roles(user, claims)
        self.update_groups(user, claims)
        self.create_oidc_user_id(user, claims.get('sub'))
        return user

    def update_user(self, user, username, claims):
        if user.username != username:
            user.username = username
            user.save()

        self.update_roles(user, claims)
        self.update_groups(user, claims)
        return user

    def filter_users_by_username(self, username):
        if not username:
            return self.UserModel.objects.none()
        return self.UserModel.objects.filter(username__iexact=username)

    def get_user_by_oidc_id(self, oidc_id):
        if oidc_id:
            ids = OIDCUserId.objects.filter(oidc_sub__iexact=oidc_id)
            if len(ids) == 1:
                return ids[0].user

    def verify_claims(self, claims) -> bool:
        self.get_username(claims)
        return True

    def get_username(self, claim) -> str:
        username = claim.get('preferred_username')
        if not username:
            raise SuspiciousOperation('No username found in claim / user_info')
        return username

    def update_groups(self, user, claims):
        is_service_account = claims.get("is_service_account", False)
        authentik_groups = claims.get('groups', [])

        if authentik_groups is None:
            if (user.is_superuser or user.is_staff or is_service_account):
                authentik_groups = []
            else:
                raise SuspiciousOperation('No group found in claim / user_info')

        # strip leading slashes if any
        authentik_groups = [g.lstrip('/') for g in authentik_groups]

        user_groups = [g.name for g in user.groups.all()]
        authentik_groups.sort()
        user_groups.sort()

        if authentik_groups != user_groups:
            with transaction.atomic():
                user.groups.clear()
                for group in authentik_groups:
                    group, _ = Group.objects.get_or_create(name=group)
                    group.user_set.add(user)

    def update_roles(self, user, claims):
        """
        If user belongs to the "admin" group → superuser/staff.
        Authentik doesn't use realm_access, so we check groups.
        """
        is_service_account = claims.get("is_service_account", False)
        authentik_groups = claims.get('groups', [])
        is_admin = 'admin' in authentik_groups or is_service_account

        if is_admin != user.is_superuser or is_admin != user.is_staff:
            user.is_superuser = is_admin
            user.is_staff = is_admin
            user.save()

    def create_oidc_user_id(self, user, user_id):
        OIDCUserId.objects.create(user=user, oidc_sub=user_id)

    def is_oidc_user_id_same(self, user, sub) -> bool:
        ids = OIDCUserId.objects.filter(pk=user)
        return len(ids) == 1 and ids[0].oidc_sub == sub

    def get_userinfo_attribute(self, user_info, key):
        value = user_info.get(key)
        if not value:
            raise SuspiciousOperation(f'Required key not found in claim: {key}')
        return value

    def archive_old_user(self, username, sub):
        user_filter = self.UserModel.objects.filter(username__iexact=username)
        for user in user_filter:
            user.username += f'-{sub}'
            user.active = False
            user.save()
