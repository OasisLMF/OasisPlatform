import datetime
import jwt
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, serializers
from rest_framework.parsers import FormParser
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView, \
    TokenObtainPairView as BaseTokenObtainPairView
from rest_framework.response import Response
from rest_framework.views import APIView
from urllib.parse import urlencode

from .serializers import OIDCAuthorizationCodeExchangeSerializer, OIDCClientCredentialsSerializer, OIDCTokenRefreshSerializer, \
    SimpleTokenObtainPairSerializer, SimpleTokenRefreshSerializer
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
    serializer_class = OIDCTokenRefreshSerializer if settings.API_AUTH_TYPE in settings.ALLOWED_OIDC_AUTH_PROVIDERS else SimpleTokenRefreshSerializer
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
    Authenticates users via simple JWT or clients via OIDC based on request data.
    """
    @swagger_auto_schema(
        responses={status.HTTP_200_OK: TokenObtainPairResponseSerializer},
        security=[],
        tags=['authentication'])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_serializer_class(self):
        request_data = self.request.data

        # If `client_id` and `client_secret` are present, use the OIDC flow
        if 'client_id' in request_data and 'client_secret' in request_data:
            if settings.API_AUTH_TYPE not in settings.ALLOWED_OIDC_AUTH_PROVIDERS:
                raise serializers.ValidationError(
                    f"OIDC client credentials flow is disabled on this server for api auth_type {settings.API_AUTH_TYPE}.")
            return OIDCClientCredentialsSerializer
        # If `username` and `password` are present, use the Simple JWT flow
        if 'username' in request_data and 'password' in request_data:
            if settings.API_AUTH_TYPE != "simple":
                raise serializers.ValidationError(
                    f"Simple JWT username/password flow is disabled on this server for api auth_type {settings.API_AUTH_TYPE}.")
            return SimpleTokenObtainPairSerializer
        raise serializers.ValidationError("ERROR: Can only call access_token with \"username AND password\" or \"client_id AND client_secret\"")


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
        if settings.API_AUTH_TYPE not in settings.ALLOWED_OIDC_AUTH_PROVIDERS:
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
        serializer = OIDCAuthorizationCodeExchangeSerializer(
            data=data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        tokens = serializer.validated_data.get('_tokens')

        session_payload = {
            "tokens": tokens,
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=1)
        }
        session_token = jwt.encode(session_payload, settings.SECRET_KEY, algorithm="HS256")

        next_url = request.GET.get('state', '/')
        redirect_url = f"{next_url}?session_token={session_token}"
        return HttpResponseRedirect(redirect_url)

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


class OIDCSessionTokenView(APIView):
    """
    Exchange a temporary session_token (received after OIDC login redirect) for an access and refresh token pair.
    Expected input:
    - session_token: The one-time identifier returned in the query string from /oidc/callback/.
    Example flow:
    1. User is redirected back to frontend with ?session_token=abc123
    2. Frontend POSTs { \"session_token\": \"abc123\" } to this endpoint
    3. Backend returns `access_token`, `refresh_token`, etc.
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'session_token': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Temporary session token obtained from OIDC callback redirect"
                )
            },
            required=['session_token']
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Access and refresh tokens successfully returned",
                schema=TokenObtainPairResponseSerializer
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Missing or invalid session_token"
            ),
        },
        security=[],
        tags=['authentication']
    )
    def post(self, request):
        session_token = request.data.get("session_token")
        if not session_token:
            return Response({"detail": "Missing session_token"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            payload = jwt.decode(session_token, settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return Response({"detail": "Expired session_token"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({"detail": "Invalid session_token"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(payload.get("tokens"))


class OIDCLogoutView(APIView):
    """
    Logs out the user from the OIDC provider and redirects back to the UI.
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'id_token_hint',
                openapi.IN_QUERY,
                description="ID token hint for OIDC logout",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={302: 'Redirect to OIDC logout endpoint'},
        security=[],
        tags=['authentication']
    )
    def get(self, request, *args, **kwargs):
        if settings.API_AUTH_TYPE not in settings.ALLOWED_OIDC_AUTH_PROVIDERS:
            return HttpResponseBadRequest("OIDC logout flow not enabled on this platform.")

        logout_endpoint = settings.OIDC_OP_ENDSESSION_ENDPOINT
        if not logout_endpoint:
            return HttpResponseBadRequest("Logout endpoint not configured for this OIDC provider.")

        id_token_hint = request.GET.get('id_token_hint')
        post_logout_redirect_uri = settings.EXTERNAL_URI  # Home page

        params = {
            'post_logout_redirect_uri': post_logout_redirect_uri,
            'id_token_hint': id_token_hint,
        }

        logout_url = f"{logout_endpoint}?{urlencode(params)}"
        return HttpResponseRedirect(logout_url)
