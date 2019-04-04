#!/usr/bin/env python
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.server.oasisapi.settings")
import django
django.setup()
from django.contrib.auth.models import User

try:
    env_username = os.environ['OASIS_ADMIN_USER']
    env_password = os.environ['OASIS_ADMIN_PASS']
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
