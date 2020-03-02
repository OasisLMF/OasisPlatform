from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import routers, permissions

from .analysis_models.viewsets import AnalysisModelViewSet, ModelSettingsView
from .analyses.viewsets import AnalysisViewSet, AnalysisSettingsView
from .portfolios.viewsets import PortfolioViewSet
from .healthcheck.views import HealthcheckView
from .data_files.viewsets import DataFileViewset
from .info.views import PerilcodesView
from .info.views import ServerInfoView

admin.autodiscover()
#app_name = 'oasisapi'

api_router = routers.DefaultRouter()
api_router.include_root_view = False
api_router.register('portfolios', PortfolioViewSet, basename='portfolio')
api_router.register('analyses', AnalysisViewSet, basename='analysis')
api_router.register('models', AnalysisModelViewSet, basename='analysis-model')
api_router.register('data_files', DataFileViewset, basename='data-file')
# api_router.register('files', FilesViewSet, basename='file')


api_info = openapi.Info(
    title="Oasis Platform",
    default_version='v1',
    description="""
# Workflow
The general workflow is as follows

1. Authenticate your client, either supply your username and password to the `/refresh_token/`
   endpoint or make a `post` request to `/access_token/` with the `HTTP_AUTHORIZATION` header
   set as `Bearer <refresh_token>`.
2. Create a portfolio (post to `/portfolios/`).
3. Add a locations file to the portfolio (post to `/portfolios/<id>/locations_file/`)
4. Create the model object for your model (post to `/models/`).
5. Create an analysis (post to `/portfolios/<id>/create_analysis`). This will generate the input files
   for the analysis.
6. Add analysis settings file to the analysis (post to `/analyses/<pk>/analysis_settings/`).
7. Run the analysis (post to `/analyses/<pk>/run/`)
8. Get the outputs (get `/analyses/<pk>/output_file/`)""",
)

schema_view = get_schema_view(
    api_info,
    public=True,
    permission_classes=(permissions.AllowAny,),
)

""" Developer note:

These are custom routes to use the endpoint 'settings'
adding the method 'def settings( .. )' fails under 
viewsets.ModelViewSet due to it overriding 
the internal Django settings object 
"""

model_settings = ModelSettingsView.as_view({
    'get': 'model_settings',
    'post': 'model_settings',
    'delete': 'model_settings'
})
analyses_settings = AnalysisSettingsView.as_view({
    'get': 'analysis_settings',
    'post': 'analysis_settings',
    'delete': 'analysis_settings'
})


urlpatterns = [
    url(r'^(?P<version>[^/]+)/models/(?P<pk>\d+)/settings/', model_settings, name='model-settings'),
    url(r'^(?P<version>[^/]+)/analyses/(?P<pk>\d+)/settings/', analyses_settings, name='analysis-settings'),
    url(r'^(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    url(r'^$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-ui'),
    url(r'^', include('src.server.oasisapi.auth.urls', namespace='auth')),
    url(r'^healthcheck/$', HealthcheckView.as_view(), name='healthcheck'),
    url(r'^oed_peril_codes/$', PerilcodesView.as_view(), name='perilcodes'),
    url(r'^server_info/$', ServerInfoView.as_view(), name='serverinfo'),
    url(r'^auth/', include('rest_framework.urls')),
    url(r'^admin/', admin.site.urls),
    url(r'^(?P<version>[^/]+)/', include(api_router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
