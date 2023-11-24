from django.conf.urls import include, url
from rest_framework.routers import SimpleRouter
from .viewsets import PortfolioViewSet

v2_api_router = SimpleRouter()
v2_api_router.include_root_view = False
v2_api_router.register('portfolios', PortfolioViewSet, basename='portfolio')

urlpatterns = [
    url(r'^(?P<version>[^/]+)/', include(v2_api_router.urls)),
]
