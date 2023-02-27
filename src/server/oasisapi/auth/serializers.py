import requests
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, AuthenticationFailed
from rest_framework_simplejwt import settings as jwt_settings
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as BaseTokenObtainPairSerializer
from rest_framework_simplejwt.serializers import TokenObtainSerializer
from rest_framework_simplejwt.serializers import TokenRefreshSerializer as BaseTokenRefreshSerializer

from .. import settings

from ..oidc.keycloak_auth import keycloak_create_connection
from urllib3.util import connection


class SimpleTokenObtainPairSerializer(BaseTokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super(SimpleTokenObtainPairSerializer, self).__init__(*args, **kwargs)

        self.fields[self.username_field].help_text = _('Your username')
        self.fields['password'].help_text = _('your password')

    def validate(self, attrs):

        data = super(SimpleTokenObtainPairSerializer, self).validate(attrs)

        data['refresh_token'] = data['refresh']
        data['access_token'] = data['access']
        data['token_type'] = 'Bearer'
        data['expires_in'] = jwt_settings.api_settings.ACCESS_TOKEN_LIFETIME.total_seconds()
        # data['expires_in'] = jwt_settings.api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()

        del data['refresh']
        del data['access']

        return data


class SimpleTokenRefreshSerializer(BaseTokenRefreshSerializer):
    refresh = None

    def validate(self, attrs):
        if 'HTTP_AUTHORIZATION' not in self.context['request'].META.keys():
            raise ValidationError({"Detail": "header 'authorization' must not be null"})

        token = self.context['request'].META['HTTP_AUTHORIZATION'][7:]  # skip 'Bearer '
        attrs['refresh'] = token

        data = super(SimpleTokenRefreshSerializer, self).validate(attrs)
        data['access_token'] = data['access']
        data['token_type'] = 'Bearer'
        data['expires_in'] = jwt_settings.api_settings.ACCESS_TOKEN_LIFETIME.total_seconds()

        if 'refresh' in data:
            data['refresh_token'] = data['refresh']

        del data['refresh']
        del data['access']

        return data


class OIDCTokenObtainPairSerializer(TokenObtainSerializer):
    """
    Token serializer to authenticate and obtain a access token from Keyloak
    """
    connection.create_connection = keycloak_create_connection

    def __init__(self, *args, **kwargs):
        super(OIDCTokenObtainPairSerializer, self).__init__(*args, **kwargs)

        self.fields[self.username_field].help_text = _('Your username')
        self.fields['password'].help_text = _('your password')

    def validate(self, attrs):

        response = requests.post(
            settings.OIDC_OP_TOKEN_ENDPOINT,
            data={
                'grant_type': 'password',
                'client_id': settings.OIDC_RP_CLIENT_ID,
                'client_secret': settings.OIDC_RP_CLIENT_SECRET,
                'scope': 'openid',
                'username': attrs.get('username', None),
                'password': attrs.get('password', None)
            },
            verify=False,
        )

        json = response.json()

        if response.status_code != 200 or 'access_token' not in json:
            raise AuthenticationFailed({'Detail': 'invalid credentials'})

        cleaned = {key: json[key] for key in ['access_token', 'refresh_token', 'token_type', 'expires_in']}

        return cleaned


class OIDCTokenRefreshSerializer(serializers.Serializer):

    """
    Token serializer to obtain a new access token from Keycloak
    """
    connection.create_connection = keycloak_create_connection

    def validate(self, attrs):
        if 'HTTP_AUTHORIZATION' not in self.context['request'].META.keys():
            raise ValidationError({"Detail": "header 'authorization' must not be null"})

        token = self.context['request'].META['HTTP_AUTHORIZATION'][7:]  # skip 'Bearer '

        response = requests.post(
            settings.OIDC_OP_TOKEN_ENDPOINT,
            data={
                'grant_type': 'refresh_token',
                'client_id': settings.OIDC_RP_CLIENT_ID,
                'client_secret': settings.OIDC_RP_CLIENT_SECRET,
                'scope': 'openid',
                'refresh_token': token
            },
            verify=False,
        )

        json = response.json()

        if response.status_code != 200 or 'access_token' not in json:
            raise AuthenticationFailed({'Detail': 'invalid refresh token'})

        cleaned = {key: json[key] for key in ['access_token', 'refresh_token', 'token_type', 'expires_in']}

        return cleaned
