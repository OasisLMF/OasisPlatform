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

This whole flow — connect, register, upload, create analysis, generate inputs, run, and
download the ORD results — was validated end-to-end against a live current platform
(PiWind on a v2 model worker). Make sure your **model worker image matches your platform
version**: a worker pinned to an old release can register but fail to run tasks against a
newer server.
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

client = APIClient(
    api_url="http://localhost:8000/api/",   # note the trailing /api/ base — endpoints hang off it
    auth_type="simple",                     # username/password auth (the default local setup)
    username="admin", password="password",
)
client.healthcheck()      # GET /api/healthcheck/
client.server_info()      # GET /api/server_info/
```

```{admonition} api_url and auth_type
:class: tip

The client builds every endpoint from `api_url` (`url_base = urljoin(api_url, '')`), so it must
include the `/api/` base **with a trailing slash** — e.g. `http://localhost:8000/api/`. Pass
`auth_type="simple"` for the standard username/password login; the other supported types are
`oidc`/`m2m` (client id/secret) and `token` (access/refresh token).
```

## Register the model

The model id is the `(supplier_id, model_id, version_id)` triple that a worker serves:

```python
model = client.models.create(supplier_id="OasisLMF", model_id="PiWind", version_id="1")
model_id = model["id"]
```

```{admonition} run_mode and version must line up with a worker
:class: important

Two things the server needs before it will accept an analysis for this model:

- **`run_mode`** must be set (`V1` or `V2`) — creating an analysis against a model with a null
  `run_mode` fails with `"'run_mode' must not be null"`. A worker sets this automatically when it
  auto-registers; if you register the model by hand, set it to match the worker, e.g.
  `client.api.patch(client.api.url_base + f"v2/models/{model_id}/", json={"run_mode": "V1"})`.
- **`version_id`** must match the version the worker serves (its task queue is keyed on
  `supplier_id-model_id-version_id`). In practice you usually let the worker auto-register the
  model rather than creating it here, so the triple always matches.
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

`download_output` writes `analysis_{id}_output.tar.gz` into `download_path`. Unpack it to get
an `output/` folder of ORD CSVs — with the settings above you get `gul_S1_ept.csv` /
`il_S1_ept.csv` (exceedance-probability tables) and `gul_S1_palt.csv` / `il_S1_palt.csv`
(period ALT), plus per-summary `*_summary-info.csv`:

```python
import tarfile
with tarfile.open("./results/analysis_%d_output.tar.gz" % analysis_id) as tar:
    tar.extractall("./results")
```

## Plot the EP curve

The EPT table is the exceedance-probability curve. `EPType` selects the metric
(1 = OEP, 2 = OEP TVaR, 3 = AEP, 4 = AEP TVaR) and `EPCalc` the statistic
(1 = mean damage, 2 = full uncertainty):

```python
import pandas as pd, matplotlib.pyplot as plt

ept = pd.read_csv("./results/output/gul_S1_ept.csv")
fu  = ept[ept["EPCalc"] == 2]                       # full uncertainty
oep = fu[fu["EPType"] == 1].sort_values("ReturnPeriod")
aep = fu[fu["EPType"] == 3].sort_values("ReturnPeriod")

fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(oep["ReturnPeriod"], oep["Loss"] / 1e6, marker="o", label="OEP (occurrence)")
ax.plot(aep["ReturnPeriod"], aep["Loss"] / 1e6, marker="s", label="AEP (aggregate)")
ax.set_xscale("log")
ax.set_xlabel("Return period (years)"); ax.set_ylabel("Loss (£m)")
ax.set_title("PiWind GUL exceedance probability curve (full uncertainty)")
ax.legend(); ax.grid(True, which="both", alpha=0.3)
```

The downloaded outputs are the ORD tables described in the OasisLMF *Outputs & results*
reference; for deeper analysis of every ORD table see the ORD-results example notebook.

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
