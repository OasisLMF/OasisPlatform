from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import routers, permissions

from .analysis_models.viewsets import AnalysisModelViewSet
from .portfolios.viewsets import PortfolioViewSet
from .analyses.viewsets import AnalysisViewSet
from .healthcheck.views import HealthcheckView
from .complex_model_files.viewsets import ComplexModelDataFileViewset

admin.autodiscover()

api_router = routers.DefaultRouter()
api_router.include_root_view = False
api_router.register('portfolios', PortfolioViewSet, base_name='portfolio')
api_router.register('analyses', AnalysisViewSet, base_name='analysis')
api_router.register('models', AnalysisModelViewSet, base_name='analysis-model')
api_router.register('complex_data_files', ComplexModelDataFileViewset, base_name='complex-model-data-file')
# api_router.register('files', FilesViewSet, base_name='file')


schema_view = get_schema_view(
    openapi.Info(
        title="Oasis Platform",
        description="""# Workflow

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
        default_version='v1',
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    url(r'^(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    url(r'^$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-ui'),
    url(r'^', include('src.server.oasisapi.auth.urls', namespace='auth')),
    url(r'^healthcheck/$', HealthcheckView.as_view(), name='healthcheck'),
    url(r'^auth/', include('rest_framework.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^(?P<version>[^/]+)/', include(api_router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
