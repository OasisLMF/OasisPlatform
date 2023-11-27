from django.conf.urls import include, url
from rest_framework.routers import SimpleRouter
from .viewsets import PortfolioViewSet


app_name = 'portfolios'
v1_api_router = SimpleRouter()
v1_api_router.include_root_view = False
v1_api_router.register('portfolios', PortfolioViewSet, basename='portfolio')

urlpatterns = [
    url(r'', include(v1_api_router.urls)),
]
