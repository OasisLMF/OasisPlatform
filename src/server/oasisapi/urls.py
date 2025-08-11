from django.conf import settings
from django.urls import include, re_path
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework import permissions

from .swagger import (
    api_v1_urlpatterns,
    api_v2_urlpatterns,
)

if settings.DEBUG_TOOLBAR:
    from django.urls import path
    import debug_toolbar


api_info_description = """
# Workflow
The general workflow is as follows
"""

if settings.API_AUTH_TYPE == 'keycloak':
    api_info_description += """
1. Authenticate your client:
    1. Post to the keycloak endpoint:
       `grant_type=password&client_id=<client-id>&client_secret=<client-secret>&username=<username>&password=<password>`
       Check your chart values to find the endpoint (`OIDC_ENDPOINT`), <client-id> (`OIDC_CLIENT_NAME`) and
       <client-secret> (`OIDC_CLIENT_SECRET`).
    2. Either supply your username and password to the `/access_token/` endpoint or make a `post` request
       to `/refresh_token/` with the `HTTP_AUTHORIZATION` header set as `Bearer <refresh_token>`.
    3. Here in swagger - click the `Authorize` button, enter 'swagger' as client_id and click Authorize. This will open
       a new window with the keycloak login, enter your credentials and click Login. This will close the window and get
       you back to the authorize dialog which you now can close."""
else:
    api_info_description += """
1. Authenticate your client, either supply your username and password to the `/access_token/`
   endpoint or make a `post` request to `/refresh_token/` with the `HTTP_AUTHORIZATION` header
   set as `Bearer <refresh_token>`."""

api_info_description += """
2. Create a portfolio (post to `/portfolios/`).
3. Add a locations file to the portfolio (post to `/portfolios/<id>/locations_file/`)
4. Create the model object for your model (post to `/models/`).
5. Create an analysis (post to `/portfolios/<id>/create_analysis`). This will generate the input files
   for the analysis.
6. Add analysis settings file to the analysis (post to `/analyses/<pk>/analysis_settings/`).
7. Run the analysis (post to `/analyses/<pk>/run/`)
8. Get the outputs (get `/analyses/<pk>/output_file/`)"""


# drf-spectacular views replace the schema views


api_urlpatterns = [
    # drf-spectacular schema and UI endpoints
    re_path(r'^schema/$', SpectacularAPIView.as_view(), name='schema'),
    re_path(r'^$', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    re_path(r'^redoc/$', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # basic urls (auth, server info)
    re_path(r'^', include('src.server.oasisapi.base_urls')),
]
api_urlpatterns += api_v1_urlpatterns
if not settings.DISABLE_V2_API:
    api_urlpatterns += api_v2_urlpatterns

urlpatterns = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.URL_SUB_PATH:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += [re_path(r'^api/', include(api_urlpatterns))]
else:
    urlpatterns += static(settings.STATIC_DEBUG_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += [re_path(r'^', include(api_urlpatterns))]


if settings.DEBUG_TOOLBAR:
    urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))
