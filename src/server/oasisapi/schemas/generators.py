from drf_spectacular.generators import SchemaGenerator


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
