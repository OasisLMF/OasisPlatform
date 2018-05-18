from flask import url_for
from flask_jwt_extended.utils import decode_token
from src.server.models import DefaultCredentials
from .base import AppTestCase
import json


class AccessToken(AppTestCase):
    def test_username_is_not_correct___response_is_401(self):
        username = 'dirk'
        password = 'supersecret'
        DefaultCredentials.create(username=username, password=password)

        url = url_for('root.refresh_token')

        response = self.client.post(
            url,
            data=json.dumps({'username': username + 'extra', 'password': password}),
            content_type='application/json'
        )

        self.assertEqual(401, response.status_code)

    def test_password_is_not_correct___response_is_401(self):
        username = 'dirk'
        password = 'supersecret'
        DefaultCredentials.create(username=username, password=password)

        url = url_for('root.refresh_token')

        response = self.client.post(
            url,
            data=json.dumps({'username': username, 'password': password + 'extra'}),
            content_type='application/json'
        )

        self.assertEqual(401, response.status_code)

    def test_username_and_password_are_correct___returned_token_represents_the_user(self):
        username = 'dirk'
        password = 'supersecret'
        user = DefaultCredentials.create(username=username, password=password).user

        url = url_for('root.refresh_token')

        response = self.client.post(
            url,
            data=json.dumps({'username': username, 'password': password}),
            content_type='application/json'
        )
        data = response.json

        expected_ident = self.app.auth_backend.get_jwt_identity(user)
        actual_refresh_ident = decode_token(data.get('refresh_token'))['identity']
        actual_access_ident = decode_token(data.get('access_token'))['identity']

        self.assertEqual(expected_ident, actual_refresh_ident)
        self.assertEqual(expected_ident, actual_access_ident)
        self.assertEqual(data['expires_in'], 3600)
        self.assertEqual(data['token_type'], 'Bearer')

    def test_username_and_password_are_correct___refresh_token_can_be_used_to_get_access_token(self):
        username = 'dirk'
        password = 'supersecret'
        user = DefaultCredentials.create(username=username, password=password).user

        url = url_for('root.refresh_token')

        response = self.client.post(
            url,
            data=json.dumps({'username': username, 'password': password}),
            content_type='application/json'
        )
        data = response.json

        url = url_for('root.access_token')
        response = self.client.post(
            url,
            content_type='application/json',
            headers={'Authorization': 'Bearer {}'.format(data['refresh_token'])}
        )
        data = response.json

        expected_ident = self.app.auth_backend.get_jwt_identity(user)
        actual_access_ident = decode_token(data.get('access_token'))['identity']

        self.assertEqual(expected_ident, actual_access_ident)
        self.assertEqual(data['expires_in'], 3600)
        self.assertEqual(data['token_type'], 'Bearer')
