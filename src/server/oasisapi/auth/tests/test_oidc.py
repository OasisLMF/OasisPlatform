import json

import mock
from django_webtest import WebTest
from rest_framework.reverse import reverse

from src.server.oasisapi import settings


class MockResponse:
    """
    HTTP mock response, to simulate response from keycloak
    """

    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


# HTTP mock rules, a dict of url and a lambda to create a MockResponse
mock_rules = {}


def mocked_requests_get(*args, **kwargs):
    """
    Mock function executed on a request.get call. Finds any matching url in mock_rules
    and runs the lamdba to get a MockResponse.

    :param args: Args to request.get
    :param kwargs: Kwargs to request.get
    :return: A MockResponse
    """

    for url, response in mock_rules.items():
        if args[0] == url:
            return response(args, data=kwargs.get('data', {}))

    return MockResponse(None, 404)


def mocked_keycloak_auth_respone(*args, **kwargs):
    """
    Mock the keycloak auth url. If the username and password match then return a access token. If not return 401.

    :param kwargs:username and password to match
    :return: MockResponse
    """

    data = kwargs.get('data')

    if data:

        if data.get('username', '') == kwargs.get('username') and data.get('password', '') == kwargs.get('password'):
            return MockResponse({
                'access_token': 'access',
                'refresh_token': 'refresh',
                'token_type': 'type',
                'expires_in': '3600'
            }, 200)

    return MockResponse({}, 401)


class TestKeycloakOIDCAuthenticationBackend(WebTest):

    def setUp(self):
        # Empty the mock_rules
        global mock_rules
        mock_rules = {}

        # Dummy values for requried settings
        settings.OIDC_OP_TOKEN_ENDPOINT = 'http://fake-host/auth'
        settings.OIDC_RP_CLIENT_ID = ''
        settings.OIDC_RP_CLIENT_SECRET = ''

    @mock.patch('requests.post', side_effect=mocked_requests_get)
    def test_access_token_valid(self, mock_post):
        """
        Test a valid authentication by posting our username/password and verify our mocked keycloak access token is
        in the response.
        """

        global mock_rules

        username = 'user123'
        password = 'password123'

        mock_rules = {'http://fake-host/auth': lambda *args, **
                      kwargs: mocked_keycloak_auth_respone(args, data=kwargs.get('data', {}), username=username, password=password)}

        response = self.app.post(
            reverse('auth:access_token'),
            params=json.dumps({'username': username, 'password': password}),
            content_type='application/json'
        )

        self.assertDictEqual(response.json, {
            "access_token": "access",
            "refresh_token": "refresh",
            "token_type": "type",
            "expires_in": "3600"
        })

    @mock.patch('requests.post', side_effect=mocked_requests_get)
    def test_access_token_invalid(self, mock_post):
        """
        Test failed login attempt.
        """

        global mock_rules

        mock_rules = {'http://fake-host/auth': lambda *args, **kwargs: mocked_keycloak_auth_respone(args)}

        response = self.app.post(
            reverse('auth:access_token'),
            params=json.dumps({'username': 'invalid', 'password': 'invalid'}),
            content_type='application/json',
            expect_errors=True,
        )

        self.assertEqual(401, response.status_code)
