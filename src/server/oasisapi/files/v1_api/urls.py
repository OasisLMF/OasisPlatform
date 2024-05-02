from django.conf.urls import include, url
from rest_framework.routers import SimpleRouter
from .viewsets import FilesViewSet, MappingFilesViewSet


app_name = 'files'
v1_api_router = SimpleRouter()
v1_api_router.include_root_view = False
v1_api_router.register('files', FilesViewSet, basename='file')
v1_api_router.register('mapping-files', MappingFilesViewSet, basename='mapping-file')


urlpatterns = [
    url(r'', include(v1_api_router.urls)),
]
