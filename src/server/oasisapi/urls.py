from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
# from rest_framework_nested import routers

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

api_info = openapi.Info(
    title="Oasis Platform",
    default_version='v2',
    description=api_info_description,
)

schema_view = get_schema_view(
    api_info,
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# Base Routes (no version)
api_urlpatterns = [
    #url(r'^(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    url(r'^v2/swagger(v2.json|v2.yaml)$', schema_view.without_ui(cache_timeout=None), name='schema-json'),
    url(r'^v1/swagger(v1.json|v1.yaml)$', schema_view.without_ui(cache_timeout=None), name='schema-json'),
    url(r'^$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-ui'),
    url(r'^', include('src.server.oasisapi.base_urls')),
]


# API v1 Routes
api_urlpatterns += [
    url(r'^v1/', include('src.server.oasisapi.analysis_models.v1_api.urls', namespace='v1-models')),
    url(r'^v1/', include('src.server.oasisapi.portfolios.v1_api.urls', namespace='v1-portfolios')),
    url(r'^v1/', include('src.server.oasisapi.analyses.v1_api.urls', namespace='v1-analyses')),
    url(r'^v1/', include('src.server.oasisapi.data_files.v1_api.urls', namespace='v1-files')),
]

# API v2 Routes
if not settings.DISABLE_V2_API:
    api_urlpatterns += [
        url(r'^v2/', include('src.server.oasisapi.analysis_models.v2_api.urls', namespace='v2-models')),
        url(r'^v2/', include('src.server.oasisapi.analyses.v2_api.urls', namespace='v2-analyses')),
        url(r'^v2/', include('src.server.oasisapi.portfolios.v2_api.urls', namespace='v2-portfolios')),
        url(r'^v2/', include('src.server.oasisapi.data_files.v2_api.urls', namespace='v2-files')),
        url(r'^v2/', include('src.server.oasisapi.queues.urls', namespace='v2-queues')),
    ]

urlpatterns = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.URL_SUB_PATH:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += [url(r'^api/', include(api_urlpatterns))]
else:
    urlpatterns += static(settings.STATIC_DEBUG_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += [url(r'^', include(api_urlpatterns))]

if settings.DEBUG_TOOLBAR:
    urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))
