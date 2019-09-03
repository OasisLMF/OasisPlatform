from django.conf.urls import url
from drf_yasg.utils import swagger_auto_schema
from .views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    url(r'^access_token/$', TokenObtainPairView.as_view(), name='access_token'),
    url(r'^refresh_token/$', TokenRefreshView.as_view(), name='refresh_token'),
]
