import json
from unittest.mock import patch

from django.urls import reverse
from django_webtest import WebTestMixin
from hypothesis import given, settings
from hypothesis.strategies import sampled_from
from hypothesis.extra.django import TestCase
from rest_framework_simplejwt.tokens import AccessToken

from src.server.oasisapi.auth.tests.fakes import fake_user, fake_group
from src.server.oasisapi.files.models import RelatedFile
from src.server.oasisapi.files.v2_api.tests.fakes import fake_mapping_file, fake_related_file


class FileConversion(WebTestMixin, TestCase):
    csrf_checks = False

    def test_user_cannot_access_the_mapping_file___error_is_raised(self):
        related_file_group, shared_group = fake_group(_quantity=2)

        user = fake_user()
        related_file_group.user_set.add(user)

        mapping_file = fake_mapping_file(groups=[shared_group])
        related_file: RelatedFile = fake_related_file(groups=[related_file_group, shared_group])

        response = self.app.post(
            reverse("v2-files:file-convert", kwargs={"pk": related_file.pk}),
            params=json.dumps({
                "mapping_file": mapping_file.pk
            }),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            content_type='application/json',
            expect_errors=True,
            user=user,
        )

        self.assertEqual(response.json, {"detail": 'You dont have permission to use the mapping file'})
        self.assertEqual(response.status_code, 403)

    def test_user_cannot_access_the_file___error_is_raised(self):
        mapping_file_group, shared_group = fake_group(_quantity=2)

        user = fake_user()
        mapping_file_group.user_set.add(user)

        mapping_file = fake_mapping_file(groups=[mapping_file_group, shared_group])
        related_file: RelatedFile = fake_related_file(groups=[shared_group])

        response = self.app.post(
            reverse("v2-files:file-convert", kwargs={"pk": related_file.pk}),
            params=json.dumps({
                "mapping_file": mapping_file.pk
            }),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            content_type='application/json',
            expect_errors=True,
            user=user,
        )

        self.assertEqual(response.json, {"detail": 'You dont have permission to run a conversion on the file'})
        self.assertEqual(response.status_code, 403)

    def test_user_is_not_part_of_the_shared_group___error_is_raised(self):
        related_file_group, mapping_file_group, shared_group = fake_group(_quantity=3)

        user = fake_user()
        related_file_group.user_set.add(user)
        mapping_file_group.user_set.add(user)

        mapping_file = fake_mapping_file(groups=[mapping_file_group, shared_group])
        related_file: RelatedFile = fake_related_file(groups=[related_file_group, shared_group])

        response = self.app.post(
            reverse("v2-files:file-convert", kwargs={"pk": related_file.pk}),
            params=json.dumps({
                "mapping_file": mapping_file.pk
            }),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            content_type='application/json',
            expect_errors=True,
            user=user,
        )

        self.assertEqual(response.json, {"detail": "The file and mapping do not share a group you are part of"})
        self.assertEqual(response.status_code, 403)

    @given(state=sampled_from([RelatedFile.ConversionState.PENDING, RelatedFile.ConversionState.IN_PROGRESS]))
    def test_file_is_not_in_a_convertable_state___error_is_raised(self, state):
        related_file_group, mapping_file_group, shared_group = fake_group(_quantity=3)

        user = fake_user()
        shared_group.user_set.add(user)

        mapping_file = fake_mapping_file(groups=[mapping_file_group, shared_group])
        related_file: RelatedFile = fake_related_file(groups=[related_file_group, shared_group], conversion_state=state)

        response = self.app.post(
            reverse("v2-files:file-convert", kwargs={"pk": related_file.pk}),
            params=json.dumps({
                "mapping_file": mapping_file.pk
            }),
            headers={
                'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
            },
            content_type='application/json',
            expect_errors=True,
            user=user,
        )

        self.assertEqual(response.json, {"detail": f"File is not in a convertable state. Current conversion state is {state}"})
        self.assertEqual(response.status_code, 400)

    @given(state=sampled_from([RelatedFile.ConversionState.NONE, RelatedFile.ConversionState.ERROR, RelatedFile.ConversionState.DONE]))
    @settings(deadline=None)
    def test_file_is_not_in_a_convertable_state___conversion_is_started(self, state):
        with patch('src.server.oasisapi.files.v2_api.tasks.run_file_conversion') as mock_task:
            related_file_group, mapping_file_group, shared_group = fake_group(_quantity=3)

            user = fake_user()
            shared_group.user_set.add(user)

            mapping_file = fake_mapping_file(groups=[mapping_file_group, shared_group])
            related_file: RelatedFile = fake_related_file(groups=[related_file_group, shared_group], conversion_state=state)

            response = self.app.post(
                reverse("v2-files:file-convert", kwargs={"pk": related_file.pk}),
                params=json.dumps({
                    "mapping_file": mapping_file.pk
                }),
                headers={
                    'Authorization': 'Bearer {}'.format(AccessToken.for_user(user))
                },
                content_type='application/json',
                user=user,
            )

            related_file.refresh_from_db()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(related_file.conversion_state, RelatedFile.ConversionState.PENDING)
            self.assertEqual(related_file.mapping_file, mapping_file)
            mock_task.delay.assert_called_once_with(related_file.pk)
