from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView, \
    TokenObtainPairView as BaseTokenObtainPairView
from .serilizers import TokenRefreshSerializer, TokenObtainPairSerializer


class TokenRefreshView(BaseTokenRefreshView):
    """
    Fetches a new authentication token from your refresh token.

    Requires the authorization header to be set using the refresh token
    from [`/refresh_token/`](#refresh_token) e.g.

        Authorization: Bearer <refresh_token>
    """
    serializer_class = TokenRefreshSerializer


class TokenObtainPairView(BaseTokenObtainPairView):
    """
    Fetches a new refresh token from your username and password.
    """
    serializer_class = TokenObtainPairSerializer
