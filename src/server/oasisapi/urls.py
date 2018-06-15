from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from rest_framework import routers

from .portfolio.viewsets import PortfolioViewSet
from .analysis.viewsets import AnalysisViewSet

admin.autodiscover()

api_router = routers.DefaultRouter()
api_router.register('portfolios', PortfolioViewSet)
api_router.register('analyses', AnalysisViewSet, base_name='analysis')

urlpatterns = [
    url(r'', include('oasisapi.auth.urls', namespace='auth')),
    url(r'', include(api_router.urls)),
    url(r'^auth/', include('rest_framework.urls')),
    url(r'^admin/', include(admin.site.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
