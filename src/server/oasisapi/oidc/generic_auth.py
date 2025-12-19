from django.contrib.auth.models import Group
from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from mozilla_django_oidc import auth
from src.server.oasisapi.oidc.common import auth_server_create_connection
from src.server.oasisapi.oidc.models import OIDCUserId

from urllib3.util import connection


class GenericOIDCAuthenticationBackend(auth.OIDCAuthenticationBackend):
    """
    Extends Mozilla Django OIDC backend.

    - Verifies JWT from OIDC Provider
    - Creates or updates a corresponding Django user
    - Syncs groups and roles from claims

    If a user is deleted in the OIDC provider, the local django user will continue to exist to keep analyses, portfolios,
    files etc from being deleted. If a new user would be created in the OIDC provider with the same username the old django
    user will be renamed to <username>-<oidc-id>.
    """

    connection.create_connection = auth_server_create_connection

    def get_or_create_user(self, access_token, id_token, payload):
        """
        Returns a User instance if 1 user is found. Creates a user if not found. Returns nothing if multiple users
        are matched.

        Create a service account user if preferred_username happens to be missing for client_credentials requests. These
        usually are fulfilled by an internally created service account, so should have a preferred_username.
        """
        user_info = self.get_userinfo(access_token, id_token, payload)
        is_service_account = user_info.get("is_service_account", False)

        sub = self.get_userinfo_attribute(user_info, 'sub')
        username = user_info.get("preferred_username", None)
        if not username and is_service_account:
            username = f"svc-{sub}"
        elif not username:
            raise SuspiciousOperation('Required key not found in claim: preferred_username')

        user = self.get_user_by_oidc_id(sub)

        if user:
            return self.update_user(user, username, user_info)
        else:
            self.archive_old_user(username, sub)
            return self.create_user(username, user_info)

    def create_user(self, username, claims):
        """
        Create a user, store the oidc user id and groups.

        :param username: Username of the user
        :param claims: User information from the JWT
        :return: A User object
        """
        user, _ = self.UserModel.objects.get_or_create(username=username)
        self.update_roles(user, claims)
        self.update_groups(user, claims)
        self.create_oidc_user_id(user, claims.get('sub'))
        return user

    def update_user(self, user, username, claims):
        """
        Update a user including username and groups.

        :param user: The user object
        :param username: Username
        :param claims: User information from the JWT
        :return:
        """
        if user.username != username:
            user.username = username
            user.save()

        self.update_roles(user, claims)
        self.update_groups(user, claims)
        return user

    def filter_users_by_username(self, username):
        """
        Find user by username

        :param username: Username
        :return: User object or none()
        """
        if not username:
            return self.UserModel.objects.none()
        return self.UserModel.objects.filter(username__iexact=username)

    def get_user_by_oidc_id(self, oidc_id):
        """
        Find a django user by given oidc user id.

        :param oidc_id: oidc user id.
        :return: A user object or None.
        """
        if oidc_id:
            ids = OIDCUserId.objects.filter(oidc_sub__iexact=oidc_id)
            if len(ids) == 1:
                return ids[0].user

    def verify_claims(self, claims) -> bool:
        """
        Verify JWT claim by extracting the username.

        :param claims: JWT claims
        """
        self.get_username(claims)
        return True

    def get_username(self, claim) -> str:
        """
        Extract OIDC username from the JWT claim.

        :param claim: JWT claim.
        :return: Username
        """
        username = claim.get('preferred_username')
        if not username:
            raise SuspiciousOperation('No username found in claim / user_info')
        return username

    def update_groups(self, user, claims):
        """
        Persist OIDC Provider groups as local Django groups.
        """
        is_service_account = claims.get("is_service_account", False)
        oidc_groups = claims.get('groups', None)

        if oidc_groups is None:
            if (user.is_superuser or user.is_staff or is_service_account):
                oidc_groups = []
            else:
                raise SuspiciousOperation('No group found in claim / user_info')

        # strip leading slashes if any
        oidc_groups = [g.lstrip('/') for g in oidc_groups]

        user_groups = [g.name for g in user.groups.all()]
        oidc_groups.sort()
        user_groups.sort()

        if oidc_groups != user_groups:
            with transaction.atomic():
                user.groups.clear()
                for group in oidc_groups:
                    group, _ = Group.objects.get_or_create(name=group)
                    group.user_set.add(user)

    def update_roles(self, user, claims):
        """
        If user belongs to the "admin" group → superuser/staff.
        """
        is_service_account = claims.get("is_service_account", False)
        oidc_groups = claims.get('groups', [])

        # strip leading slashes if any
        oidc_groups = [g.lstrip('/') for g in oidc_groups]

        is_admin = 'admin' in oidc_groups or is_service_account

        if is_admin != user.is_superuser or is_admin != user.is_staff:
            user.is_superuser = is_admin
            user.is_staff = is_admin
            user.save()

    def create_oidc_user_id(self, user, user_id):
        """
        Create a oidc user id model and bind it to the user. This is used to verify that the oidc user haven't
        changed.

        :param user: Django user object
        :param user_id: OIDC user id
        """
        OIDCUserId.objects.create(user=user, oidc_sub=user_id)

    def is_oidc_user_id_same(self, user, sub) -> bool:
        """
        Verify the user and oidc user id is identical.

        :param user: Django user
        :param sub: OIDC user id from the JWT
        :return: True if they are identical, False otherwise.
        """
        ids = OIDCUserId.objects.filter(pk=user)
        return len(ids) == 1 and ids[0].oidc_sub == sub

    def get_userinfo_attribute(self, user_info, key):
        """
        Get key from user info (JWT claim) or raise an exception is missing.

        :param user_info: User info (JWT claim)
        :param key: Name of attribute/key
        :return: Value of key or exception it not existing
        """
        value = user_info.get(key)
        if not key:
            raise SuspiciousOperation(f'Required key not found in claim: {key}')
        return value

    def archive_old_user(self, username, sub):
        """
        Check if the username exists and if that is the case rename the user. This is used to free the username
        for a new oidc user (created with a previously existing username) but still keep all resources bound
        to user.

        :param username: Username
        :param sub: OIDC user id. Used for renaming the user to a unique name.
        """
        user_filter = self.UserModel.objects.filter(username__iexact=username)

        for user in user_filter:
            # check for and remove exisiting users before rename
            new_username = f'{user.username}-{sub}'
            self.UserModel.objects.filter(username=new_username).delete()

            user.username = new_username
            user.active = False
            user.save()
