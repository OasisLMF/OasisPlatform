import json

from django.urls import reverse
from django_webtest import WebTest
from rest_framework_simplejwt.state import token_backend

from .fakes import fake_user


class AccessToken(WebTest):
    def test_username_is_not_correct___response_is_401(self):
        username = 'dirk'
        password = 'supersecret'

        fake_user(username=username, password=password)

        response = self.app.post(
            reverse('auth:access_token'),
            params=json.dumps({'username': username + 'extra', 'password': password}),
            content_type='application/json',
            expect_errors=True,
        )

        self.assertEqual(401, response.status_code)

    def test_password_is_not_correct___response_is_401(self):
        username = 'dirk'
        password = 'supersecret'

        fake_user(username=username, password=password)

        response = self.app.post(
            reverse('auth:access_token'),
            params=json.dumps({'username': username, 'password': password + 'extra'}),
            content_type='application/json',
            expect_errors=True,
        )

        self.assertEqual(401, response.status_code)

    def test_username_and_password_are_correct___returned_token_represents_the_user(self):
        username = 'dirk'
        password = 'supersecret'

        user = fake_user(username=username, password=password)

        response = self.app.post(
            reverse('auth:access_token'),
            params=json.dumps({'username': username, 'password': password}),
            content_type='application/json'
        )
        data = response.json

        actual_refresh_ident = token_backend.decode(data.get('refresh_token').encode())
        actual_access_ident = token_backend.decode(data.get('access_token').encode())

        self.assertEqual(user.id, actual_refresh_ident['user_id'])
        self.assertEqual(user.id, actual_access_ident['user_id'])
        self.assertEqual(data['expires_in'], 3600)
        self.assertEqual(data['token_type'], 'Bearer')


class RefreshToken(WebTest):
    def test_username_and_password_are_correct___refresh_token_can_be_used_to_get_access_token(self):
        username = 'dirk'
        password = 'supersecret'

        user = fake_user(username=username, password=password)

        response = self.app.post(
            reverse('auth:access_token'),
            params=json.dumps({'username': username, 'password': password}),
            content_type='application/json'
        )

        response = self.app.post(
            reverse('auth:refresh_token'),
            content_type='application/json',
            headers={'Authorization': 'Bearer {}'.format(response.json['refresh_token'])}
        )
        data = response.json

        actual_access_ident = token_backend.decode(data.get('access_token').encode())

        self.assertEqual(user.id, actual_access_ident['user_id'])
        self.assertEqual(data['expires_in'], 3600)
        self.assertEqual(data['token_type'], 'Bearer')
