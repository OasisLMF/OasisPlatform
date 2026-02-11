from django.conf import settings
from django.urls import include, re_path
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .swagger import (
    api_v1_urlpatterns,
    api_v2_urlpatterns,
    filter_v1_endpoints,
    filter_v2_endpoints,
)

if settings.DEBUG_TOOLBAR:
    from django.urls import path
    import debug_toolbar


api_info_description = """
# Workflow
The general workflow is as follows
"""

if settings.API_AUTH_TYPE in settings.ALLOWED_OIDC_AUTH_PROVIDERS:
    api_info_description += """
### Authentication Overview

Your application can authenticate either as a **service** or as a **user**.
Two different flows are supported:
---
## 1. Service Authentication (Client Credentials Flow)

This flow is intended for service-to-service communication where no user is involved.
1. **Request an access token**
   - Make a POST request to the `/access_token/` endpoint with:
     ```
     grant_type=client_credentials
     client_id=<client-id>
     client_secret=<client-secret>
     ```
   - The response will include an `access_token` and an optional `refresh_token` (depending on configuration).
2. **Use the token**
   - Include the access token in the `Authorization` header when calling protected endpoints:
     ```
     Authorization: Bearer <access_token>
     ```
3. **Refresh the token**
   - When the access token expires, request a new one using the same `client_credentials` flow, you cannot call `/refresh_token/` for OIDC client_credentials
---
## 2. User Authentication (Authorization Code Flow with Session Token)

This flow is intended for authenticating end-users through OpenID Connect.
1. **Authorize the user**
   - Redirect the user's browser to the `oidc/authorize/` endpoint, including the client and redirect parameters.
   - Example:
     ```
     GET /oidc/authorize/?client_id=<client-id>&redirect_uri=<redirect-uri>&response_type=code&scope=openid&next=<callback-url>
     ```
   - The user will log in via the identity provider (e.g., Keycloak, Authentik) and be redirected back to your configured callback URL by the OIDC provider automatically.
2. **Handle the authorization callback**
   - Your callback endpoint (e.g., `/oidc/callback/`) will receive a short-lived `session_token` (valid for about one minute).
   - This session token contains encoded information allowing you to retrieve the user's access and refresh tokens.
3. **Exchange the session token**
   - Make a POST request to the `/oidc/session_token/` endpoint with:
     ```
     session_token=<session-token>
     ```
   - The response will contain the user's `access_token` and `refresh_token`.
4. **Use the tokens**
   - Include the user's access token in the `Authorization` header when making API calls:
     ```
     Authorization: Bearer <access_token>
     ```
5. **Refreshing tokens**
   - When the access token expires, use the `/refresh_token/` endpoint with:
     ```
     grant_type=refresh_token
     refresh_token=<refresh_token>
     ```
   - to obtain a new access token.
---
## 3. Swagger Authentication
In Swagger UI:
1. Click the **Authorize** button.
2. Enter the client_id and client_secret and click **Authorize**. This will open a new window with your OIDC login page where you enter credentials and click login.
3. You should get redirected back to the api page with the authorize dialog.
"""
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

# Set the description into SPECTACULAR_SETTINGS at import time
settings.SPECTACULAR_SETTINGS['DESCRIPTION'] = api_info_description


class SpectacularV1SchemaView(SpectacularAPIView):
    custom_settings = {
        'PREPROCESSING_HOOKS': [
            'drf_spectacular.hooks.preprocess_exclude_path_format',
            'src.server.oasisapi.swagger.filter_v1_endpoints',
        ],
    }


class SpectacularV2SchemaView(SpectacularAPIView):
    custom_settings = {
        'PREPROCESSING_HOOKS': [
            'drf_spectacular.hooks.preprocess_exclude_path_format',
            'src.server.oasisapi.swagger.filter_v2_endpoints',
        ],
    }


api_urlpatterns = [
    # Main Swagger page - schema endpoints
    re_path(r'^schema/$', SpectacularAPIView.as_view(), name='schema'),
    re_path(r'^$', SpectacularSwaggerView.as_view(url_name='schema'), name='schema-ui'),
    # V1 only swagger endpoints
    re_path(r'^v1/schema/$', SpectacularV1SchemaView.as_view(), name='schema-v1'),
    re_path(r'^v1/$', SpectacularSwaggerView.as_view(url_name='schema-v1'), name='schema-ui-v1'),
    # V2 only swagger endpoints
    re_path(r'^v2/schema/$', SpectacularV2SchemaView.as_view(), name='schema-v2'),
    re_path(r'^v2/$', SpectacularSwaggerView.as_view(url_name='schema-v2'), name='schema-ui-v2'),
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
