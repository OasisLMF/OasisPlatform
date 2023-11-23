from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.parsers import FormParser
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView, \
    TokenObtainPairView as BaseTokenObtainPairView

from .serializers import OIDCTokenRefreshSerializer, OIDCTokenObtainPairSerializer, SimpleTokenObtainPairSerializer, \
    SimpleTokenRefreshSerializer
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
    serializer_class = OIDCTokenRefreshSerializer if settings.API_AUTH_TYPE == 'keycloak' else SimpleTokenRefreshSerializer
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
    serializer_class = OIDCTokenObtainPairSerializer if settings.API_AUTH_TYPE == 'keycloak' else SimpleTokenObtainPairSerializer

    @swagger_auto_schema(
        responses={status.HTTP_200_OK: TokenObtainPairResponseSerializer},
        security=[],
        tags=['authentication'])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
