from drf_spectacular.generators import SchemaGenerator


def remove_session_auth(result, generator, request, public, **kwargs):
    """Postprocessing hook: remove auto-generated security schemes not used by this deployment.

    - cookieAuth: always removed (SessionAuthentication is present for DRF but the API
      uses token-based auth, not session cookies)
    - jwtAuth: removed when OIDC auth mode is active (JWT scheme is irrelevant then)
    """
    from django.conf import settings as django_settings

    schemes = result.get('components', {}).get('securitySchemes', {})
    schemes.pop('cookieAuth', None)

    if django_settings.API_AUTH_TYPE in django_settings.ALLOWED_OIDC_AUTH_PROVIDERS:
        schemes.pop('jwtAuth', None)

    return result


class OasisSchemaGenerator(SchemaGenerator):
    """Custom schema generator that disables NamespaceVersioning during schema generation.

    NamespaceVersioning is incompatible with drf-spectacular because the mock requests
    used during generation lack URL namespace resolution, causing determine_version()
    to return None and all endpoints to be skipped.

    V1/V2 endpoint separation is handled by PREPROCESSING_HOOKS instead.
    """

    def _get_paths_and_endpoints(self):
        for path, path_regex, method, view in super()._get_paths_and_endpoints():
            view.versioning_class = None
            yield path, path_regex, method, view
