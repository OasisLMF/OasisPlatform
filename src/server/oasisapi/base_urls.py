from django.conf.urls import include, url
from django.contrib import admin

from .info.views import PerilcodesView
from .info.views import ServerInfoView
from .healthcheck.views import HealthcheckViewDeep, HealthcheckViewShallow

# app_name = 'base'

urlpatterns = [
    url(r'^healthcheck/$', HealthcheckViewShallow.as_view(), name='healthcheck'),
    url(r'^healthcheck_connections/$', HealthcheckViewDeep.as_view(), name='healthcheck_deep'),
    url(r'^oed_peril_codes/$', PerilcodesView.as_view(), name='perilcodes'),
    url(r'^server_info/$', ServerInfoView.as_view(), name='serverinfo'),
    url(r'^auth/', include('rest_framework.urls')),
    url(r'^', include('src.server.oasisapi.auth.urls', namespace='auth')),
    url(r'^admin/', admin.site.urls),
]
