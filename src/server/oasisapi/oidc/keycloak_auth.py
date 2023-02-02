from django.contrib.auth.models import Group
from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from mozilla_django_oidc import auth

from src.server.oasisapi.oidc.models import KeycloakUserId


class KeycloakOIDCAuthenticationBackend(auth.OIDCAuthenticationBackend):
    """
    Extends Mozilla Django OIDC backend to support a better Keycloak implementation.

    Each authentication will verify the JWT from keycloak and:
     - Make sure there is a django user representation.
     - Update username, groups etc from keycloak.

     If a user is deleted in keycloak the local django user will continue to exist to keep analyses, portfolios,
     files etc from being deleted. If a new user would be created in keycloak with the same username the old django
     user will be renamed to <username>-<keycloak-id>.

    """

    def get_or_create_user(self, access_token, id_token, payload):
        """
        Returns a User instance if 1 user is found. Creates a user if not found. Returns nothing if multiple users
        are matched.
        """

        user_info = self.get_userinfo(access_token, id_token, payload)
        sub = self.get_userinfo_attribute(user_info, 'sub')
        username = self.get_userinfo_attribute(user_info, 'preferred_username')

        user = self.get_user_by_keycloak_id(sub)

        if user:

            return self.update_user(user, username, user_info)
        else:

            self.archive_old_user(username, sub)
            return self.create_user(username, user_info)

    def create_user(self, username, claims):
        """
        Create a user, store the keycloak user id and groups.

        :param username: Username of the user
        :param claims: User information from the JWT
        :return: A User object
        """

        user = self.UserModel.objects.create_user(username)
        self.update_groups(user, claims)
        self.update_roles(user, claims)
        self.create_keycloak_user_id(user, claims.get('sub'))
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

    def get_user_by_keycloak_id(self, keycloak_id):
        """
        Find a django user by given keycloak user id.

        :param keycloak_id: Keycloak user id.
        :return: A user object or None.
        """

        if keycloak_id:
            keycloak_ids = KeycloakUserId.objects.filter(keycloak_user_id__iexact=keycloak_id)

            if len(keycloak_ids) == 1:
                return keycloak_ids[0].user

    def verify_claims(self, claims) -> bool:
        """
        Verify JWT claim by extracting the username.

        :param claims: JWT claims
        """
        self.get_username(claims)
        return True

    def get_username(self, claim) -> str:
        """
        Extract Keycloaks username from the JWT claim.

        :param claim: JWT claim.
        :return: Username
        """

        username = claim.get('preferred_username')

        if not username:
            msg = 'No username found in claim / user_info'
            raise SuspiciousOperation(msg)

        return username

    def update_groups(self, user, claims):
        """
        Persist Keycloak groups as local Django groups.
        """
        keycloak_groups = claims.get('groups', [])
        for i, keycloak_group in enumerate(keycloak_groups):
            if keycloak_group.startswith('/'):
                keycloak_groups[i] = keycloak_group[1:]

        user_groups = list()
        for user_group in user.groups.all():
            user_groups.append(user_group.name)

        keycloak_groups.sort()
        user_groups.sort()

        if keycloak_groups != user_groups:
            with transaction.atomic():
                user.groups.clear()
                for group in keycloak_groups:
                    group, _ = Group.objects.get_or_create(name=group)
                    group.user_set.add(user)

    def update_roles(self, user, claims):
        """
        If a user belongs to the group admin we will enable django attributes is_superuser and is_admin.
        """
        keycloak_roles = claims.get('realm_access', dict()).get('roles', [])

        is_admin = 'admin' in keycloak_roles
        if is_admin != user.is_superuser or is_admin != user.is_staff:
            user.is_superuser = is_admin
            user.is_staff = is_admin
            user.save()

    def create_keycloak_user_id(self, user, user_id):
        """
        Create a keycloak user id model and bind it to the user. This is used to verify that the keycloak user haven't
        changed.

        :param user: Django user object
        :param user_id: Keycloak user id
        """

        KeycloakUserId.objects.create(user=user, keycloak_user_id=user_id)

    def is_keycloak_user_id_same(self, user, sub) -> bool:
        """
        Verify the user and keycloak user id is identical.

        :param user: Django user
        :param sub: Keycloak user id from the JWT
        :return: True if they are identical, False otherwise.
        """

        filter = KeycloakUserId.objects.filter(pk=user)

        return len(filter) == 1 and filter[0].keycloak_user_id == sub

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
        for a new keycloak user (created with a previously existing username) but still keep all resources bound
        to user.

        :param username: Username
        :param sub: Keycloak user id. Used for renaming the user to a unique name.
        """

        user_filter = self.UserModel.objects.filter(username__iexact=username)

        for user in user_filter:

            user.username += f'-{sub}'
            user.active = False
            user.save()
