from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView, \
    TokenObtainPairView as BaseTokenObtainPairView
from .serilizers import TokenRefreshSerializer, TokenObtainPairSerializer


class TokenRefreshView(BaseTokenRefreshView):
    serializer_class = TokenRefreshSerializer


class TokenObtainPairView(BaseTokenObtainPairView):
    serializer_class = TokenObtainPairSerializer
