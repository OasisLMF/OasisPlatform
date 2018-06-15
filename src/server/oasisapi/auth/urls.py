from django.conf.urls import url
from .views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    url(r'^refresh_token/$', TokenObtainPairView.as_view(), name='refresh_token'),
    url(r'^access_token/$', TokenRefreshView.as_view(), name='access_token'),
]
