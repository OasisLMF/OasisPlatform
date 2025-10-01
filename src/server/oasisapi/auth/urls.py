from django.urls import re_path
from .views import OIDCAuthorizeView, OIDCCallbackView, TokenObtainPairView, TokenRefreshView, ServiceTokenObtainPairView
app_name = 'auth'

urlpatterns = [
    re_path(r'^service/access_token/$', ServiceTokenObtainPairView.as_view(), name='service_access_token'),
    re_path(r'^access_token/$', TokenObtainPairView.as_view(), name='access_token'),
    re_path(r'^refresh_token/$', TokenRefreshView.as_view(), name='refresh_token'),
    re_path(r'^oidc/authorize/$', OIDCAuthorizeView.as_view(), name='oidc_authorize'),
    re_path(r'^oidc/callback/$', OIDCCallbackView.as_view(), name='oidc_callback'),
]
