__all__ = [
    'CustomGeneratorClassV1',
    'CustomGeneratorClassV2',
]

from drf_yasg.generators import OpenAPISchemaGenerator
from django.conf.urls import include, url
from django.conf import settings


# API v1 Routes
api_v1_urlpatterns = [
    url(r'^v1/', include('src.server.oasisapi.analysis_models.v1_api.urls', namespace='v1-models')),
    url(r'^v1/', include('src.server.oasisapi.portfolios.v1_api.urls', namespace='v1-portfolios')),
    url(r'^v1/', include('src.server.oasisapi.analyses.v1_api.urls', namespace='v1-analyses')),
    url(r'^v1/', include('src.server.oasisapi.data_files.v1_api.urls', namespace='v1-data-files')),
    url(r'^v1/', include('src.server.oasisapi.files.v1_api.urls', namespace='v1-files')),
]

# API v2 Routes
api_v2_urlpatterns = [
    url(r'^v2/', include('src.server.oasisapi.analysis_models.v2_api.urls', namespace='v2-models')),
    url(r'^v2/', include('src.server.oasisapi.analyses.v2_api.urls', namespace='v2-analyses')),
    url(r'^v2/', include('src.server.oasisapi.portfolios.v2_api.urls', namespace='v2-portfolios')),
    url(r'^v2/', include('src.server.oasisapi.data_files.v2_api.urls', namespace='v2-data-files')),
    url(r'^v2/', include('src.server.oasisapi.files.v2_api.urls', namespace='v2-files')),
    url(r'^v2/', include('src.server.oasisapi.queues.urls', namespace='v2-queues')),
]

if settings.URL_SUB_PATH:
    swagger_v1_urlpatterns = [url(r'^api/', include(api_v1_urlpatterns))]
    swagger_v2_urlpatterns = [url(r'^api/', include(api_v2_urlpatterns))]
else:
    swagger_v1_urlpatterns = api_v1_urlpatterns
    swagger_v2_urlpatterns = api_v2_urlpatterns


class CustomGeneratorClassV1(OpenAPISchemaGenerator):
    def __init__(self, info, version='', url=None, patterns=None, urlconf=None):
        super().__init__(
            info=info,
            version='v1',
            url=url,
            patterns=swagger_v1_urlpatterns,
            urlconf=urlconf
        )


class CustomGeneratorClassV2(OpenAPISchemaGenerator):
    def __init__(self, info, version='', url=None, patterns=None, urlconf=None):
        super().__init__(
            info=info,
            version='v2',
            url=url,
            patterns=swagger_v2_urlpatterns,
            urlconf=urlconf
        )
