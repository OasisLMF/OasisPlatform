# oasisapi/swagger.py
__all__ = [
    'CustomGeneratorClassV1',
    'CustomGeneratorClassV2',
]

from drf_spectacular.generators import SchemaGenerator
from django.urls import include, re_path
from django.conf import settings


# API v1 Routes
api_v1_urlpatterns = [
    re_path(r'^v1/', include('src.server.oasisapi.analysis_models.v1_api.urls', namespace='v1-models')),
    re_path(r'^v1/', include('src.server.oasisapi.portfolios.v1_api.urls', namespace='v1-portfolios')),
    re_path(r'^v1/', include('src.server.oasisapi.analyses.v1_api.urls', namespace='v1-analyses')),
    re_path(r'^v1/', include('src.server.oasisapi.data_files.v1_api.urls', namespace='v1-data-files')),
    # re_path(r'^v1/', include('src.server.oasisapi.files.v1_api.urls', namespace='v1-files')), LOT3 DISABLE
]

# API v2 Routes
api_v2_urlpatterns = [
    re_path(r'^v2/', include('src.server.oasisapi.analysis_models.v2_api.urls', namespace='v2-models')),
    re_path(r'^v2/', include('src.server.oasisapi.analyses.v2_api.urls', namespace='v2-analyses')),
    re_path(r'^v2/', include('src.server.oasisapi.portfolios.v2_api.urls', namespace='v2-portfolios')),
    re_path(r'^v2/', include('src.server.oasisapi.data_files.v2_api.urls', namespace='v2-data-files')),
    # re_path(r'^v2/', include('src.server.oasisapi.files.v2_api.urls', namespace='v2-files')), LOT3 DISABLE
    re_path(r'^v2/', include('src.server.oasisapi.queues.urls', namespace='v2-queues')),
]

if settings.URL_SUB_PATH:
    swagger_v1_urlpatterns = [re_path(r'^api/', include(api_v1_urlpatterns))]
    swagger_v2_urlpatterns = [re_path(r'^api/', include(api_v2_urlpatterns))]
else:
    swagger_v1_urlpatterns = api_v1_urlpatterns
    swagger_v2_urlpatterns = api_v2_urlpatterns


class CustomGeneratorClassV1(SchemaGenerator):
    def __init__(self, info, version='', url=None, patterns=None, urlconf=None):
        super().__init__(
            info=info,
            api_version='v1',
            url=url,
            patterns=swagger_v1_urlpatterns,
            urlconf=urlconf
        )


class CustomGeneratorClassV2(SchemaGenerator):
    def __init__(self, info, version='', url=None, patterns=None, urlconf=None):
        super().__init__(
            info=info,
            api_version='v2',
            url=url,
            patterns=swagger_v2_urlpatterns,
            urlconf=urlconf
        )
