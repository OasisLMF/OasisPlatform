# oasisapi/urls.py
from django.conf import settings
from django.urls import include, re_path
from django.conf.urls.static import static

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from .swagger import (
    api_v1_urlpatterns,
    api_v2_urlpatterns,
    CustomGeneratorClassV1,
    CustomGeneratorClassV2,
)

if settings.DEBUG_TOOLBAR:
    from django.urls import path
    import debug_toolbar


# -------- API Docs --------
schema_view_all = SpectacularAPIView.as_view(
    serve_public=True,
    api_version="v2",
)

schema_view_v1 = SpectacularAPIView.as_view(
    serve_public=True,
    generator_class=CustomGeneratorClassV1,
    api_version="v1",
)

schema_view_v2 = SpectacularAPIView.as_view(
    serve_public=True,
    generator_class=CustomGeneratorClassV2,
    api_version="v2",
)


api_urlpatterns = [
    # Main schema endpoints
    re_path(r'^schema$', schema_view_all, name='schema'),
    re_path(r'^$', SpectacularSwaggerView.as_view(url_name='schema'), name='schema-ui'),

    # V1 only schema
    re_path(r'^v1/schema$', schema_view_v1, name='schema-v1'),
    re_path(r'^v1/$', SpectacularSwaggerView.as_view(url_name='schema-v1'), name='schema-ui-v1'),

    # V2 only schema
    re_path(r'^v2/schema$', schema_view_v2, name='schema-v2'),
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
