from drf_yasg.utils import swagger_auto_schema
from rest_framework.parsers import FormParser
from rest_framework import status
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView, \
    TokenObtainPairView as BaseTokenObtainPairView
from .serializers import TokenRefreshSerializer, TokenObtainPairSerializer

from ..schemas.serializers import TokenObtainPairResponseSerializer, TokenRefreshResponseSerializer
from ..schemas.custom_swagger import TOKEN_REFRESH_HEADER


class TokenRefreshView(BaseTokenRefreshView):
    """
    Fetches a new authentication token from your refresh token.

    Requires the authorization header to be set using the refresh token
    from [`/refresh_token/`](#refresh_token) e.g.

        Authorization: Bearer <refresh_token>
    """
    serializer_class = TokenRefreshSerializer
    parser_classes = [FormParser]

    @swagger_auto_schema(
        manual_parameters=[TOKEN_REFRESH_HEADER],
        responses={status.HTTP_200_OK: TokenRefreshResponseSerializer})
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class TokenObtainPairView(BaseTokenObtainPairView):
    """
    Fetches a new refresh token from your username and password.
    """
    serializer_class = TokenObtainPairSerializer

    @swagger_auto_schema(responses={status.HTTP_200_OK: TokenObtainPairResponseSerializer})
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
