from django.urls import re_path

from .views import (
    ExternalEnrichView,
    ExternalJobDetailView,
    ExternalJobListView,
    ExternalLocationFileView,
    ExternalProviderSettingsView,
)

app_name = 'external_providers'

_PROVIDER = r'(?P<provider>[a-zA-Z0-9_-]+)'
_PORTFOLIO = r'(?P<portfolio_pk>\d+)'
_JOB = r'(?P<job_id>[0-9a-f-]{36})'

urlpatterns = [
    re_path(
        rf'^providers/{_PROVIDER}/portfolios/{_PORTFOLIO}/external_location_file/$',
        ExternalLocationFileView.as_view(),
        name='external-location-file',
    ),
    re_path(
        rf'^providers/{_PROVIDER}/portfolios/{_PORTFOLIO}/external_enrich/$',
        ExternalEnrichView.as_view(),
        name='external-enrich',
    ),
    re_path(
        rf'^providers/{_PROVIDER}/portfolios/{_PORTFOLIO}/external_jobs/{_JOB}/$',
        ExternalJobDetailView.as_view(),
        name='external-job-detail',
    ),
    re_path(
        rf'^providers/{_PROVIDER}/portfolios/{_PORTFOLIO}/external_jobs/$',
        ExternalJobListView.as_view(),
        name='external-job-list',
    ),
    re_path(
        rf'^external_provider_settings/{_PROVIDER}/$',
        ExternalProviderSettingsView.as_view(),
        name='external-provider-settings',
    ),
]
