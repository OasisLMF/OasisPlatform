import requests
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, AuthenticationFailed
from rest_framework_simplejwt import settings as jwt_settings
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as BaseTokenObtainPairSerializer
from rest_framework_simplejwt.serializers import TokenObtainSerializer
from rest_framework_simplejwt.serializers import TokenRefreshSerializer as BaseTokenRefreshSerializer
from rest_framework_simplejwt.tokens import AccessToken

from .. import settings

from ..oidc.common import auth_server_create_connection
from urllib3.util import connection


class SimpleServiceTokenObtainPairSerializer(BaseTokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super(SimpleServiceTokenObtainPairSerializer, self).__init__(*args, **kwargs)

        self.fields.pop(self.username_field, None)
        self.fields.pop("password", None)

    def validate(self, attrs):
        User = get_user_model()
        service_user, _ = User.objects.get_or_create(
            username="service",
            defaults={"is_active": True, "is_staff": False, "is_superuser": False}
        )

        token = AccessToken.for_user(service_user)

        return {
            "access_token": str(token),
            "token_type": "Bearer",
            "expires_in": int(token.lifetime.total_seconds()),
        }


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


class OIDCServiceTokenObtainPairSerializer(TokenObtainSerializer):
    """
    Token serializer to authenticate against the configured OIDC provider
    (Keycloak or Authentik) and obtain an access token.
    """
    connection.create_connection = auth_server_create_connection

    def __init__(self, *args, **kwargs):
        super(OIDCServiceTokenObtainPairSerializer, self).__init__(*args, **kwargs)

        self.fields.pop(self.username_field, None)
        self.fields.pop("password", None)

    def validate(self, attrs):

        response = requests.post(
            settings.OIDC_OP_TOKEN_ENDPOINT,
            data={
                'grant_type': 'client_credentials',
                'client_id': settings.OIDC_RP_SERVICE_CLIENT_ID,
                'client_secret': settings.OIDC_RP_SERVICE_CLIENT_SECRET,
                'scope': 'openid profile',
            },
            verify=False,
        )

        json = response.json()

        if response.status_code != 200 or 'access_token' not in json:
            raise AuthenticationFailed({'Detail': 'invalid credentials'})

        allowed_keys = ["access_token", "token_type", "expires_in"]

        # Only include refresh_token if it exists in the response
        if "refresh_token" in json:
            allowed_keys.append("refresh_token")

        cleaned = {key: json[key] for key in allowed_keys if key in json}

        return cleaned


class OIDCTokenObtainPairSerializer(TokenObtainSerializer):
    """
    Token serializer to authenticate against the configured OIDC provider
    (Keycloak or Authentik) and obtain an access token.
    """
    connection.create_connection = auth_server_create_connection

    def __init__(self, *args, **kwargs):
        super(OIDCTokenObtainPairSerializer, self).__init__(*args, **kwargs)

        self.fields.pop(self.username_field, None)
        self.fields.pop("password", None)

    def validate(self, attrs):

        response = requests.post(
            settings.OIDC_OP_TOKEN_ENDPOINT,
            data={
                'grant_type': 'client_credentials',
                'client_id': settings.OIDC_RP_CLIENT_ID,
                'client_secret': settings.OIDC_RP_CLIENT_SECRET,
                'scope': 'openid',
            },
            verify=False,
        )

        json = response.json()

        if response.status_code != 200 or 'access_token' not in json:
            raise AuthenticationFailed({'Detail': 'invalid credentials'})

        allowed_keys = ["access_token", "token_type", "expires_in"]

        # Only include refresh_token if it exists in the response
        if "refresh_token" in json:
            allowed_keys.append("refresh_token")

        cleaned = {key: json[key] for key in allowed_keys if key in json}

        return cleaned


class OIDCTokenRefreshSerializer(serializers.Serializer):
    """
    Token serializer to refresh tokens using the configured OIDC provider.
    """
    connection.create_connection = auth_server_create_connection

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


class OIDCBaseSerializer(serializers.Serializer):
    """
    Base to ensure the urllib3 connection hack for OIDC Provider is applied if needed.
    """

    def __init__(self, *args, **kwargs):
        connection.create_connection = auth_server_create_connection
        super().__init__(*args, **kwargs)


class OIDCAuthorizationCodeExchangeSerializer(OIDCBaseSerializer):
    """
    Exchanges an authorization code for tokens.
    Expected input:
      - code (from OIDC redirect)
    """
    code = serializers.CharField(required=True)
    redirect_uri = serializers.CharField(required=False, allow_null=True)

    def validate(self, attrs):
        code = attrs.get('code')
        redirect_uri = attrs.get('redirect_uri') or settings.OIDC_AUTH_CODE_REDIRECT_URI

        client_id = settings.OIDC_RP_CLIENT_ID
        client_secret = settings.OIDC_RP_CLIENT_SECRET

        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'client_secret': client_secret
        }

        response = requests.post(
            settings.OIDC_OP_TOKEN_ENDPOINT,
            data=data,
            verify=False
        )

        try:
            json_data = response.json()
        except Exception:
            raise AuthenticationFailed({'Detail': 'Invalid response from OIDC provider'})

        if response.status_code != 200 or 'access_token' not in json_data:
            raise AuthenticationFailed({'Detail': 'invalid authorization code'})

        cleaned = {
            'access_token': json_data.get('access_token'),
            'token_type': json_data.get('token_type'),
            'expires_in': json_data.get('expires_in'),
            'refresh_token': json_data.get('refresh_token') if 'refresh_token' in json_data else None,
        }
        attrs['_tokens'] = cleaned
        return attrs
