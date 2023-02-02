from collections.abc import Iterable

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
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


def add_fake_group(user, group_name):
    group, _ = Group.objects.get_or_create(name=group_name)
    group.user_set.add(user)
    user.save()
    return group
