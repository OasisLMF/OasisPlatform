__all__ = [
    'filter_v1_endpoints',
    'filter_v2_endpoints',
]

from django.urls import include, re_path
# from django.conf import settings


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


def filter_v1_endpoints(endpoints, **kwargs):
    """Preprocessing hook: keep only v1 endpoints (and shared endpoints that aren't v2-specific)."""
    return [e for e in endpoints if '/v1/' in e[0] or '/v2/' not in e[0]]


def filter_v2_endpoints(endpoints, **kwargs):
    """Preprocessing hook: keep only v2 endpoints (and shared endpoints that aren't v1-specific)."""
    return [e for e in endpoints if '/v2/' in e[0] or '/v1/' not in e[0]]
