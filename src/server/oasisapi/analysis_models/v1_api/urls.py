from django.conf.urls import include, url
from rest_framework_nested import routers
from .viewsets import AnalysisModelViewSet, ModelSettingsView, SettingsTemplateViewSet


app_name = 'models'
v1_api_router = routers.SimpleRouter()
v1_api_router.register('models', AnalysisModelViewSet, basename='analysis-model')

v1_templates_router = routers.NestedSimpleRouter(v1_api_router, r'models', lookup='models')
v1_templates_router.register('setting_templates', SettingsTemplateViewSet, basename='models-setting_templates')

model_settings = ModelSettingsView.as_view({
    'get': 'model_settings',
    'post': 'model_settings',
    'delete': 'model_settings'
})

urlpatterns = [
    url(r'models/(?P<pk>\d+)/settings/', model_settings, name='model-settings'),
    url(r'', include(v1_api_router.urls)),
    url(r'', include(v1_templates_router.urls)),
]
