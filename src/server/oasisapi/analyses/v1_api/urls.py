#from rest_framework_nested import routers
from rest_framework.routers import SimpleRouter
from .viewsets import AnalysisViewSet, AnalysisSettingsView, AnalysisTaskStatusViewSet
from django.conf.urls import include, url

v1_api_router = SimpleRouter()
v1_api_router.include_root_view = False
v1_api_router.register('analyses', AnalysisViewSet, basename='analysis')
v1_api_router.register('analysis-task-statuses', AnalysisTaskStatusViewSet, basename='analysis-task-status')

analyses_settings = AnalysisSettingsView.as_view({
    'get': 'analysis_settings',
    'post': 'analysis_settings',
    'delete': 'analysis_settings'
})

urlpatterns = [
    url(r'^(?P<version>[^/]+)/analyses/(?P<pk>\d+)/settings/', analyses_settings, name='analysis-settings'),
    url(r'^(?P<version>[^/]+)/', include(v1_api_router.urls)),
]    
