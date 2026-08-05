# Runbook — validate the Platform-API how-to end to end (local Docker)

A reproducible, local bring-up of the Oasis Platform used to validate
[`docs/source/how-to/run-analysis-via-api.md`](source/how-to/run-analysis-via-api.md)
end to end: build images → start the v2 stack → register/upload/generate/run/download →
plot the EP curve → tear down.

> Uses a version-matched `:dev` image pair (server + worker built from the same repo) so
> there is no engine/version mismatch.

## Set your paths

Point these at your local checkouts / data (adjust to wherever you cloned the repos):

```bash
export OASIS_PLATFORM_DIR="$HOME/OasisPlatform"                 # OasisPlatform repo
export OASIS_MODEL_DATA_DIR="$HOME/OasisPiWind"                 # PiWind model package (mounted into the worker)
export OED_INPUTS="$HOME/OasisModels/PiWind/tests/test_1"       # example OED location/accounts CSVs
export PYBIN="$HOME/venv_3.12/bin/python"                       # a Python env with oasislmf + pandas + matplotlib
```

## 0. One-time — make `docker` usable in your shell

The `docker` group must be active in your session, and a single Docker daemon should own the
socket (if a snap Docker and apt `docker-ce` are both installed, disable one — the confined
snap daemon cannot stop/kill containers):

```bash
newgrp docker                          # this shell only — or log out & back in for all shells
docker info | grep "Server Version"    # expect a normal daemon, no permission error
```

## 1. One-time — build the images (skip if already present)

```bash
cd "$OASIS_PLATFORM_DIR"
docker images | grep -E "api_server|model_worker"   # if both :dev exist, skip
docker compose -p oasisval build server v2-worker   # otherwise build the matched pair
```

## 2. Bring up the platform (v2 services only)

Point the worker mount at the PiWind model package and start just the v2 services. **Do not**
use a bare `docker compose up -d` — it also starts the pinned `stable-worker` (old release)
which fails on a version mismatch.

```bash
cd "$OASIS_PLATFORM_DIR"
# OASIS_MODEL_DATA_DIR is read by the compose file for the worker volume mount

docker compose -p oasisval up -d \
  server server-websocket \
  v2-worker-monitor v2-task-controller v2-worker \
  channel-layer
```

`server-websocket` is required: without it the worker's progress-ping errors into
`stderror.err` and the kernel guard aborts the run.

## 3. Wait until ready

```bash
# API server (runs DB migrations on first start, ~30-40s)
until curl -sf http://localhost:8000/api/healthcheck/ >/dev/null; do sleep 3; done; echo "API up"

# worker auto-registered the model?
docker logs oasisval-v2-worker-1 2>&1 | grep -i "register_worker: SUPPLIER_ID"
# -> ...SUPPLIER_ID=OasisLMF, MODEL_ID=PiWind, VERSION_ID=v2
```

The worker auto-registers `OasisLMF/PiWind/v2` with `run_mode=V2`, so you do **not** need to
create the model by hand — reference `model_id=1`.

## 4. Analysis settings

Save as `analysis_settings_e2e.json` in your working directory. EPT + ALT only — `elt_sample`
crashes eltpy on empty partitions, and `ri_output` is false because we upload only location +
accounts:

```json
{
  "analysis_tag": "e2e", "model_name_id": "PiWind", "model_supplier_id": "OasisLMF",
  "gul_threshold": 0, "number_of_samples": 10, "gul_output": true,
  "model_settings": { "event_set": "p", "event_occurrence_id": "lt" },
  "gul_summaries": [ { "id": 1, "ord_output": {
      "alt_period": true, "ept_full_uncertainty_aep": true,
      "ept_full_uncertainty_oep": true, "return_period_file": true, "parquet_format": false } } ],
  "il_output": true,
  "il_summaries": [ { "id": 1, "ord_output": {
      "alt_period": true, "ept_full_uncertainty_aep": true,
      "ept_full_uncertainty_oep": true, "return_period_file": true, "parquet_format": false } } ],
  "ri_output": false
}
```

## 5. Run the workflow (Jupyter or a Python REPL)

Run from the Python env in `$PYBIN` (or a Jupyter kernel using it):

```python
import os
from oasislmf.platform_api.client import APIClient

client = APIClient(api_url="http://localhost:8000/api/",   # note the /api/ base
                   auth_type="simple", username="admin", password="password")
client.healthcheck()

oed = os.environ["OED_INPUTS"]
pf = client.upload_inputs(portfolio_name="e2e",
                          location_fp=f"{oed}/SourceLocOEDPiWind.csv",
                          accounts_fp=f"{oed}/SourceAccOEDPiWind.csv")

a = client.create_analysis(portfolio_id=pf["id"], model_id=1,   # 1 = auto-registered PiWind/v2
                           analysis_name="e2e",
                           analysis_settings_fp="analysis_settings_e2e.json")
aid = a["id"]

client.run_generate(aid)     # generate_inputs + poll -> READY
client.run_analysis(aid)     # run + poll            -> RUN_COMPLETED
client.download_output(aid, download_path="./results")
```

Unpack and plot the EP curve:

```python
import tarfile, pandas as pd, matplotlib.pyplot as plt
with tarfile.open(f"./results/analysis_{aid}_output.tar.gz") as tar:
    tar.extractall("./results")

ept = pd.read_csv("./results/output/gul_S1_ept.csv")
fu  = ept[ept.EPCalc == 2]                              # full uncertainty
oep = fu[fu.EPType == 1].sort_values("ReturnPeriod")    # 1=OEP, 3=AEP
aep = fu[fu.EPType == 3].sort_values("ReturnPeriod")

fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(oep.ReturnPeriod, oep.Loss / 1e6, marker="o", label="OEP")
ax.plot(aep.ReturnPeriod, aep.Loss / 1e6, marker="s", label="AEP")
ax.set_xscale("log"); ax.set_xlabel("Return period (years)"); ax.set_ylabel("Loss (£m)")
ax.legend(); ax.grid(True, which="both", alpha=0.3); plt.show()
```

Expect a ~117-row EPT and a 200-year OEP around £1,460m.

## 6. Tear down

```bash
cd "$OASIS_PLATFORM_DIR"
docker compose -p oasisval down -v      # removes containers, volumes, network
docker ps -a --filter name=oasisval     # should be empty
```

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `permission denied ... /var/run/docker.sock` | Group not active in shell — `newgrp docker` or re-login. |
| `cannot stop/kill container: permission denied` | Two Docker daemons installed (e.g. snap + apt); the confined one can't kill. Disable one so a single daemon owns the socket. |
| Client 404 on `/healthcheck/` | `api_url` must include the `/api/` base **with trailing slash**. |
| `Missing credentials for auth_type 'None'` | Pass `auth_type="simple"`. |
| Analysis create 400 `'run_mode' must not be null` | Let the worker auto-register the model, or `client.api.patch(url_base+f"v2/models/{id}/", json={"run_mode":"V2"})`. |
| Run aborts, `stderror.err` has `oasis_ping_websocket ... name resolution` | `server-websocket` not running — start it. |
| Run aborts, eltpy `IndexError: index 0 out of bounds ... size 0` | Remove `elt_sample` from the ORD output (empty-partition bug). |
| Task stuck `INPUTS_GENERATION_QUEUED` | v2 orchestration missing — ensure `v2-worker-monitor` + `v2-task-controller` are up. |
| `stable-worker` crash-loops (`No module named 'psycopg'`) | Old pinned worker vs current backend — don't start it; use `v2-worker`. |
