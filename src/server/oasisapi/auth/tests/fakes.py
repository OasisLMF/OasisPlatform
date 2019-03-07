from collections import Iterable

from django.contrib.auth import get_user_model
from model_mommy import mommy


def fake_user(**kwargs):
    password = kwargs.pop('password', 'password')
    kwargs.setdefault('is_active', True)

    users = mommy.make(get_user_model(), **kwargs)

    if password:
        for user in users if isinstance(users, Iterable) else [users]:
            user.set_password(password)
            user.save()

    return users
