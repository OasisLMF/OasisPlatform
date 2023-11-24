from django.conf.urls import include, url
from rest_framework.routers import SimpleRouter
from .viewsets import _

v2_api_router = SimpleRouter()
v2_api_router.include_root_view = False


v2_api_router.register()

urlpatterns = [
    url(r'^(?P<version>[^/]+)/', include(v2_api_router.urls)),
]
