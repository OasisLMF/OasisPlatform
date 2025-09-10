from django.urls import include, re_path
from rest_framework_nested import routers
from .viewsets import AnalysisModelViewSet, ModelSettingsView, SettingsTemplateViewSet


app_name = 'models'
v2_api_router = routers.SimpleRouter()
v2_api_router.register('models', AnalysisModelViewSet, basename='analysis-model')

v2_templates_router = routers.NestedSimpleRouter(v2_api_router, r'models', lookup='models')
v2_templates_router.register('setting_templates', SettingsTemplateViewSet, basename='models-setting_templates')

model_settings = ModelSettingsView.as_view({
    'get': 'model_settings',
    'post': 'model_settings',
    'delete': 'model_settings'
})

urlpatterns = [
    re_path(r'models/(?P<pk>\d+)/settings/', model_settings, name='model-settings'),
    re_path(r'', include(v2_api_router.urls)),
    re_path(r'', include(v2_templates_router.urls)),
]
