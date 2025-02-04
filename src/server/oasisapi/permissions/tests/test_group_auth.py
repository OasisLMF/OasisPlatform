from unittest import TestCase
from uuid import uuid4

import pytest
from django.contrib.auth.models import User, Group
from rest_framework.exceptions import ValidationError

from src.server.oasisapi.permissions.group_auth import verify_and_get_groups


def create_user(groups):

    user = User.objects.create_user('testuser' + str(uuid4()))
    for group in groups:
        group, _ = Group.objects.get_or_create(name=group)
        group.user_set.add(user)
    user.save()

    return user


@pytest.mark.django_db
class TestGroupAuth(TestCase):

    def test_verify_and_get_groups__no_or_empty(self):

        user_no_group = create_user([])

        self.assertEqual([], verify_and_get_groups(user_no_group, None))
        self.assertEqual([], verify_and_get_groups(user_no_group, []))

    def test_verify_and_get_groups__invalid_groups(self):

        g1, _ = Group.objects.get_or_create(name='g1')
        g2, _ = Group.objects.get_or_create(name='g2')

        user_no_group = create_user([])
        user_1_group = create_user([g1])

        self.assertRaises(ValidationError, verify_and_get_groups, user_no_group, [g1])
        self.assertRaises(ValidationError, verify_and_get_groups, user_1_group, [])
        self.assertRaises(ValidationError, verify_and_get_groups, user_1_group, [g2])

    def test_verify_and_get_groups__valid_groups(self):

        g1, _ = Group.objects.get_or_create(name='g1')
        g2, _ = Group.objects.get_or_create(name='g2')

        user_1_group = create_user([g1])
        user_2_group = create_user([g1, g2])

        self.assertEqual([g1], verify_and_get_groups(user_1_group, [g1]))
        self.assertEqual([g1], verify_and_get_groups(user_2_group, [g1]))
        self.assertEqual([g1, g2], verify_and_get_groups(user_2_group, [g1, g2]))

    def test_verify_and_get_groups(self):

        g1, _ = Group.objects.get_or_create(name='g1')
        g2, _ = Group.objects.get_or_create(name='g2')

        user_no_group = create_user([])
        user_1_group = create_user([g1])
        user_2_group = create_user([g1, g2])

        # Verify no or empty groups for a user without groups
        self.assertEqual(0, len(verify_and_get_groups(user_no_group, None)))
        self.assertEqual(0, len(verify_and_get_groups(user_no_group, [])))

        # Verify groups can be set to empty if the user has groups
        self.assertRaises(ValidationError, verify_and_get_groups, user_1_group, [])

        # Verify groups are set to users default
        self.assertEqual(1, len(verify_and_get_groups(user_1_group, None)))

        # Verify users are in the group
        self.assertEqual(1, len(verify_and_get_groups(user_1_group, [g1])))
        self.assertEqual(2, len(verify_and_get_groups(user_2_group, [g1, g2])))
        self.assertEqual(1, len(verify_and_get_groups(user_1_group, [g1, g2])))
