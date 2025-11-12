#!/usr/bin/env python
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.server.oasisapi.settings")
import django
django.setup()
from django.contrib.auth.models import User

try:
    # The default django admin user is created here only when "simple" apiAuthType is used.
    # For OIDC, the users are created by the OIDC provider and backend classes.

    if not bool(os.environ.get('OASIS_USE_OIDC', False)):
        env_username = os.environ.get('OASIS_SERVICE_USERNAME_OR_ID', '')
        env_password = os.environ.get('OASIS_SERVICE_PASSWORD_OR_SECRET', '')

        # backwards compatibly
        if not env_username:
            env_username = os.environ.get('OASIS_ADMIN_USER', '')
        if not env_password:
            env_password = os.environ.get('OASIS_ADMIN_PASSWORD', '')

        if env_username and env_password:
            try:
                print('Creating user: "{}"'.format(env_username))
                u = User.objects.get(username=env_username)
                u.set_password(env_password)
                u.save()
                print('User creation complete')
            except Exception as e:
                User.objects.create_superuser(env_username, 'admin@example.com', env_password)
                print(str(e))
except KeyError:
    print('User Enviroment vars not set')
