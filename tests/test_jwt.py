from flask import url_for
from src.server.models import db, user_datastore
from .base import AppTestCase
import json


class AccessToken(AppTestCase):
    def setUp(self):
        super(AccessToken, self).setUp()
        self.username = 'dirk'
        self.password = 'supersecret'
        self.user = user_datastore.create_user(username=self.username, password=self.password)
        db.session.commit()

    def test_username_and_password_are_correct___returned_token_represents_the_user(self):
        url = url_for('root.access_token')

        response = self.client.post(
            url,
            data=json.dumps({'username': self.username, 'password': self.password}),
            content_type='application/json'
        )
        data = response.json
        self.assertIsNotNone(data.get('access_token'))
        self.assertEqual(data['expires_in'], 3600)
