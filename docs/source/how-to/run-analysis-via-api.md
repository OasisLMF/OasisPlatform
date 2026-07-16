# Run an analysis via the Platform API

This guide drives the Oasis Platform programmatically with the Python API client
(`oasislmf.platform_api.client.APIClient`) — register a model, upload exposure, create
and run an analysis, and download the ORD results. The same steps are available from the
CLI (`oasislmf api ...`).

```{admonition} This is a documentation guide, not an executed notebook
:class: note

Running an analysis needs a **running platform** (the API server, Celery workers, broker,
databases and a model worker with model data) — so these cells are **not executed when the
docs are built**. Bring the platform up yourself (below) and run the steps against it. Every
call maps to a route in the persisted [Platform v2 API](../reference/platform_v2) schema.
```

## Prerequisites

Bring the platform up with Docker Compose (from the repository root):

```bash
docker compose up -d
# API at http://localhost:8000  (default credentials admin / password)
```

You also need a **model loaded on a worker** (e.g. PiWind — see the Kubernetes/Helm docs
or the compose model-worker configuration) and an OED exposure set
(`SourceLocOEDPiWind.csv`, `SourceAccOEDPiWind.csv`) and an `analysis_settings.json`
(an example is in this repo's `docs/` folder).

## Connect

```python
from oasislmf.platform_api.client import APIClient

client = APIClient(api_url="http://localhost:8000", username="admin", password="password")
client.healthcheck()      # GET /api/healthcheck/
client.server_info()      # GET /api/server_info/
```

## Register the model

The model id is the `(supplier_id, model_id, version_id)` triple that a worker serves:

```python
model = client.models.create(supplier_id="OasisLMF", model_id="PiWind", version_id="1")
model_id = model["id"]
```

## Upload exposure (creates a portfolio)

```python
portfolio = client.upload_inputs(
    portfolio_name="PiWind portfolio",
    location_fp="SourceLocOEDPiWind.csv",
    accounts_fp="SourceAccOEDPiWind.csv",
)
portfolio_id = portfolio["id"]
```

`upload_inputs` creates the portfolio and uploads the OED files
(`POST /api/v2/portfolios/`, then `.../location_file/` and `.../accounts_file/`).

## Create the analysis

```python
analysis = client.create_analysis(
    portfolio_id=portfolio_id,
    model_id=model_id,
    analysis_name="PiWind base run",
    analysis_settings_fp="analysis_settings.json",   # uploaded to .../settings/
)
analysis_id = analysis["id"]
```

## Generate inputs, then run

Both steps are asynchronous on the workers; the client submits and polls the task status
until complete:

```python
client.run_generate(analysis_id)    # POST /api/v2/analyses/{id}/generate_inputs/ + poll
client.run_analysis(analysis_id)    # POST /api/v2/analyses/{id}/run/ + poll
```

## Download the results

```python
client.download_output(analysis_id, download_path="./results")
# GET /api/v2/analyses/{id}/output_file/  -> the ORD result tables (SELT, EPT, ALT, ...)
```

The downloaded outputs are the ORD tables described in the OasisLMF *Outputs & results*
reference; analyse them as in the ORD-results example notebook.

## CLI equivalent

The same end-to-end flow is available from the command line:

```bash
oasislmf api run --api-server-url http://localhost:8000 \
  --model-supplier-id OasisLMF --model-name-id PiWind --model-version-id 1 \
  --oed-location-csv SourceLocOEDPiWind.csv --oed-accounts-csv SourceAccOEDPiWind.csv \
  --analysis-settings-json analysis_settings.json --output-dir ./results
```

## Where next

- {doc}`../reference/platform_v2` — the full interactive Platform v2 API reference.
- {doc}`first-steps` — a minimal Docker + API walk-through.
