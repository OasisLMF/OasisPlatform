from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from rest_framework import routers
from rest_framework.documentation import include_docs_urls

from .analysis_models.viewsets import AnalysisModelViewSet
from .portfolios.viewsets import PortfolioViewSet
from .analyses.viewsets import AnalysisViewSet

admin.autodiscover()

api_router = routers.DefaultRouter()
api_router.include_root_view = False
api_router.register('portfolios', PortfolioViewSet, base_name='portfolio')
api_router.register('analyses', AnalysisViewSet, base_name='analysis')
api_router.register('models', AnalysisModelViewSet, base_name='analysis-model')

urlpatterns = [
    url(r'^', include('src.server.oasisapi.auth.urls', namespace='auth')),
    #url(r'^', include('rest_framework_docs.urls')),
    url(r'^', include_docs_urls(title='Oasis Platform', public=True, permission_classes=[])),
    url(r'^', include(api_router.urls)),
    url(r'^auth/', include('rest_framework.urls')),
    url(r'^admin/', include(admin.site.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
