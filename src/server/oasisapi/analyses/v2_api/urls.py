from django.conf.urls import include, url
from rest_framework.routers import SimpleRouter
from .viewsets import AnalysisViewSet, AnalysisSettingsView, AnalysisTaskStatusViewSet


app_name = 'analyses'
v2_api_router = SimpleRouter()
v2_api_router.include_root_view = False
v2_api_router.register('analyses', AnalysisViewSet, basename='analysis')
v2_api_router.register('analysis-task-statuses', AnalysisTaskStatusViewSet, basename='analysis-task-status')

analyses_settings = AnalysisSettingsView.as_view({
    'get': 'analysis_settings',
    'post': 'analysis_settings',
    'delete': 'analysis_settings'
})


urlpatterns = [
    url(r'analyses/(?P<pk>\d+)/settings/', analyses_settings, name='analysis-settings'),
    url(r'', include(v2_api_router.urls)),
]    
