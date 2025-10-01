from django.http import HttpResponseBadRequest, HttpResponseRedirect
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.parsers import FormParser
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView, \
    TokenObtainPairView as BaseTokenObtainPairView
from rest_framework.response import Response
from rest_framework.views import APIView
from urllib.parse import urlencode

from .serializers import OIDCAuthorizationCodeExchangeSerializer, OIDCServiceTokenObtainPairSerializer, OIDCTokenRefreshSerializer, OIDCTokenObtainPairSerializer, \
    SimpleServiceTokenObtainPairSerializer, SimpleTokenObtainPairSerializer, SimpleTokenRefreshSerializer
from .. import settings
from ..schemas.custom_swagger import TOKEN_REFRESH_HEADER
from ..schemas.serializers import TokenObtainPairResponseSerializer, TokenRefreshResponseSerializer


class TokenRefreshView(BaseTokenRefreshView):
    """
    Fetches a new authentication token from your refresh token.

    Requires the authorization header to be set using the refresh token
    from [`/refresh_token/`](#refresh_token) e.g.

        Authorization: Bearer <refresh_token>
    """
    serializer_class = OIDCTokenRefreshSerializer if settings.API_AUTH_TYPE in settings.SUPPORTED_OIDC_PROVIDERS else SimpleTokenRefreshSerializer
    parser_classes = [FormParser]

    @swagger_auto_schema(
        manual_parameters=[TOKEN_REFRESH_HEADER],
        responses={status.HTTP_200_OK: TokenRefreshResponseSerializer},
        security=[],
        tags=['authentication'])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class TokenObtainPairView(BaseTokenObtainPairView):
    """
    Fetches a new refresh token from your username and password.
    """
    serializer_class = OIDCTokenObtainPairSerializer if settings.API_AUTH_TYPE in settings.SUPPORTED_OIDC_PROVIDERS else SimpleTokenObtainPairSerializer

    @swagger_auto_schema(
        responses={status.HTTP_200_OK: TokenObtainPairResponseSerializer},
        security=[],
        tags=['authentication'])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ServiceTokenObtainPairView(BaseTokenObtainPairView):
    """
    Fetches a new refresh token from your username and password.
    """
    serializer_class =\
        OIDCServiceTokenObtainPairSerializer if settings.API_AUTH_TYPE in settings.SUPPORTED_OIDC_PROVIDERS else SimpleServiceTokenObtainPairSerializer

    @swagger_auto_schema(
        responses={status.HTTP_200_OK: TokenObtainPairResponseSerializer},
        security=[],
        tags=['authentication'])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class OIDCAuthorizeView(APIView):
    """
    Initiate the authorization code flow by redirecting the browser to OIDC auth endpoint.
    Query args:
      - next (optional): path to redirect back to after successful authentication
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'next',
                openapi.IN_QUERY,
                description="Optional path to redirect back to after successful authentication",
                type=openapi.TYPE_STRING,
                required=False,
            )
        ],
        responses={302: 'Redirect to OIDC authorization endpoint'},
        security=[],
        tags=['authentication']
    )
    def get(self, request, *args, **kwargs):
        if settings.API_AUTH_TYPE not in settings.SUPPORTED_OIDC_PROVIDERS:
            return HttpResponseBadRequest("OIDC authorization flow not enabled on this platform.")

        client_id = settings.OIDC_RP_CLIENT_ID
        redirect_uri = settings.OIDC_AUTH_CODE_REDIRECT_URI

        next_url = request.GET.get('next', '/')
        state = next_url

        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid profile email",
            "state": state
        }
        auth_url = f"{settings.OIDC_OP_AUTHORIZATION_ENDPOINT}?{urlencode(params)}"
        return HttpResponseRedirect(auth_url)


class OIDCCallbackView(APIView):
    """
    Endpoint that OIDC Provider redirects back to after the user logs in (authorization code).
    This view accepts 'code' and exchanges it for tokens using client_id/secret of the auth-code client.
    POSTs or GETs are accepted (GET for redirect callback).
    """
    permission_classes = [AllowAny]
    parser_classes = [FormParser]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'code',
                openapi.IN_QUERY,
                description="Authorization code from OIDC Provider",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'state',
                openapi.IN_QUERY,
                description="State parameter (redirect destination)",
                type=openapi.TYPE_STRING,
                required=False
            )
        ],
        responses={status.HTTP_200_OK: TokenObtainPairResponseSerializer},
        security=[],
        tags=['authentication']
    )
    def get(self, request, *args, **kwargs):
        data = {
            'code': request.GET.get('code'),
            'state': request.GET.get('state'),
        }
        serializer = OIDCAuthorizationCodeExchangeSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        tokens = serializer.validated_data.get('_tokens')

        next_url = request.GET.get('state', '/')
        return Response(tokens, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=OIDCAuthorizationCodeExchangeSerializer,
        responses={status.HTTP_200_OK: TokenObtainPairResponseSerializer},
        security=[],
        tags=['authentication'])
    def post(self, request, *args, **kwargs):
        serializer = OIDCAuthorizationCodeExchangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        tokens = serializer.validated_data.get('_tokens')
        return Response(tokens, status=status.HTTP_200_OK)
