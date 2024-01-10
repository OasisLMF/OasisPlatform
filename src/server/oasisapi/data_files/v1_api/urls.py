from django.conf.urls import include, url
from rest_framework.routers import SimpleRouter
from .viewsets import DataFileViewset


app_name = 'data_files'
v1_api_router = SimpleRouter()
v1_api_router.include_root_view = False
v1_api_router.register('data_files', DataFileViewset, basename='data-file')

urlpatterns = [
    url(r'', include(v1_api_router.urls)),
]
