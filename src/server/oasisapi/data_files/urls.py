from django.conf.urls import include, url
from rest_framework.routers import SimpleRouter
from .viewsets import DataFileViewset

api_router = SimpleRouter()
api_router.include_root_view = False
api_router.register('data_files', DataFileViewset, basename='data-file')

urlpatterns = [
    url(r'^(?P<version>[^/]+)/', include(api_router.urls)),
]
