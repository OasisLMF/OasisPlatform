from django.conf.urls import include, url
from rest_framework.routers import SimpleRouter
from rest_framework_nested import routers
from .viewsets import AnalysisModelViewSet, ModelSettingsView, SettingsTemplateViewSet

v2_api_router = SimpleRouter()
v2_api_router.include_root_view = False
v2_api_router.register('models', AnalysisModelViewSet, basename='analysis-model')
v2_templates_router = routers.NestedSimpleRouter(v2_api_router, r'models', lookup='models')
v2_templates_router.register('setting_templates', SettingsTemplateViewSet, basename='models-setting_templates')

model_settings = ModelSettingsView.as_view({
    'get': 'model_settings',
    'post': 'model_settings',
    'delete': 'model_settings'
})

urlpatterns = [
    url(r'^(?P<version>[^/]+)/models/(?P<pk>\d+)/settings/', model_settings, name='model-settings'),
    url(r'^(?P<version>[^/]+)/', include(v2_api_router.urls)),
    url(r'^(?P<version>[^/]+)/', include(v2_templates_router.urls)),
]
