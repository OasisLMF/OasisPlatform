# Reference

## REST API

Overview and route reference for the platform REST API:

```{toctree}
:maxdepth: 1

rest_api
API
```

### Interactive API reference (OpenAPI)

The full **Platform v1 / v2** REST APIs, rendered from their OpenAPI schemas:

```{toctree}
:maxdepth: 1

platform_v2
platform_v1
```

```{admonition} How the schemas are kept current
:class: note

The OpenAPI schemas are **persisted in-repo** under `_static/schemas/` and rendered here
with redoc. They are generated from the Django app with drf-spectacular
(`.github/workflows/build-schema.yml`); a CI step should regenerate and commit them on
release so they track the code (replacing the manually-committed snapshot). This fixes the
previous situation where the schemas existed only as short-lived CI artifacts. Example
`analysis_settings.json` / `.xsd` are in the repo `docs/` folder; the settings *schemas*
themselves are owned by ODS Tools.
```
