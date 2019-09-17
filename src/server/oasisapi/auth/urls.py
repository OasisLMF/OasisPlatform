from django.conf.urls import url
from .views import TokenObtainPairView, TokenRefreshView
app_name = 'auth'

urlpatterns = [
    url(r'^access_token/$', TokenObtainPairView.as_view(), name='access_token'),
    url(r'^refresh_token/$', TokenRefreshView.as_view(), name='refresh_token'),
]
