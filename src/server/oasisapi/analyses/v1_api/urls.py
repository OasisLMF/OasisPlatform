from django.conf.urls import include, url
from rest_framework.routers import SimpleRouter
from .viewsets import AnalysisViewSet, AnalysisSettingsView


v1_api_router = SimpleRouter()
v1_api_router.include_root_view = False
v1_api_router.register('analyses', AnalysisViewSet, basename='analysis')

analyses_settings = AnalysisSettingsView.as_view({
    'get': 'analysis_settings',
    'post': 'analysis_settings',
    'delete': 'analysis_settings'
})

urlpatterns = [
    url(r'analyses/(?P<pk>\d+)/settings/', analyses_settings, name='analysis-settings'),
    url(r'', include(v1_api_router.urls)),
]
