from django.urls import include, re_path
from django.contrib import admin

from .info.views import PerilcodesView
from .info.views import ServerInfoView
from .healthcheck.views import HealthcheckViewDeep, HealthcheckViewShallow

# app_name = 'base'

urlpatterns = [
    re_path(r'^healthcheck/$', HealthcheckViewShallow.as_view(), name='healthcheck'),
    re_path(r'^healthcheck_connections/$', HealthcheckViewDeep.as_view(), name='healthcheck_deep'),
    re_path(r'^oed_peril_codes/$', PerilcodesView.as_view(), name='perilcodes'),
    re_path(r'^server_info/$', ServerInfoView.as_view(), name='serverinfo'),
    re_path(r'^auth/', include('rest_framework.urls')),
    re_path(r'^', include('src.server.oasisapi.auth.urls', namespace='auth')),
    re_path(r'^admin/', admin.site.urls),
]
