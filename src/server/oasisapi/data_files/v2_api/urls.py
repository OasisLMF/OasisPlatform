from django.urls import include, re_path
from rest_framework.routers import SimpleRouter
from .viewsets import DataFileViewset


app_name = 'data_files'
v2_api_router = SimpleRouter()
v2_api_router.include_root_view = False
v2_api_router.register('data_files', DataFileViewset, basename='data-file')

urlpatterns = [
    re_path(r'', include(v2_api_router.urls)),
]
