from django.urls import include, re_path
from rest_framework.routers import SimpleRouter
from .viewsets import FilesViewSet, MappingFilesViewSet


app_name = 'files'
v1_api_router = SimpleRouter()
v1_api_router.include_root_view = False
v1_api_router.register('files', FilesViewSet, basename='file')
v1_api_router.register('mapping-files', MappingFilesViewSet, basename='mapping-file')


urlpatterns = [
    re_path(r'', include(v1_api_router.urls)),
]
