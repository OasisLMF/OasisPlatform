from flask import url_for
from flask_jwt_extended.utils import get_jwt_identity
from base64 import decode
from src.server.models import db, DefaultCredentials
from .base import AppTestCase
import json


class AccessToken(AppTestCase):
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
        self.assertIsNotNone(data.get('access_token'))
        self.assertEqual(data['expires_in'], 3600)
