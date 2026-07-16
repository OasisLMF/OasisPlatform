# Reference

## REST API

```{toctree}
:maxdepth: 1

rest_api
API
```

```{admonition} OpenAPI schemas
:class: note

The Platform **v1** and **v2** REST APIs are described by OpenAPI schemas generated
from the Django app with drf-spectacular (`.github/workflows/build-schema.yml`). These
are currently produced as CI artifacts; a follow-up will **persist them in-repo** and
render them here with redoc (as the aggregated site does today). Example
`analysis_settings.json` / `.xsd` are in the repo `docs/` folder.
```
