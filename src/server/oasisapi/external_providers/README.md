# external_providers

Django app implementing provider-agnostic external exposure-data integration. GXM is the first concrete provider. See `docs/tmp_claude/Oasis_GXM_Integration.md` for the full design.

## Enabling the feature

The feature is off by default. Set in `conf.ini` or via environment variable:

```ini
[server]
EXTERNAL_PROVIDERS_ENABLED = true
GXM_BASE_URL = https://api.gxm.example
GXM_CLIENT_ID = <your-client-id>
GXM_CLIENT_SECRET = <your-client-secret>
```

When `EXTERNAL_PROVIDERS_ENABLED` is false, all new endpoints return 404 and existing behaviour is unchanged.

## Running against the dummy GXM service

```sh
# In the dummy-gxm-service repo:
docker compose up --build -d

# In OasisPlatform:
export OASIS_EXTERNAL_PROVIDERS_ENABLED=1
export OASIS_GXM_BASE_URL=http://localhost:8000
export OASIS_GXM_CLIENT_ID=oasis-dev
export OASIS_GXM_CLIENT_SECRET=not-a-real-secret

# UC1 — fetch country exposure
curl -X POST "$OASIS/api/v2/providers/gxm/portfolios/42/external_location_file/" \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"country_code":"GH","format":"parquet"}'
# → 202 { "job_id": "...", "status": "PENDING", "status_url": "..." }

# Poll until COMPLETED
curl "$OASIS/api/v2/providers/gxm/portfolios/42/external_jobs/<job_id>/"
```

## Known gaps / next steps

### 1. OED validation before persisting (services.py)

`run_location_file` and `run_enrich` currently write the provider response straight to `RelatedFile` without an OED schema check. The validator is already available — the portfolio model uses it for user-uploaded files via `run_oed_validation_signature()`. The call should be added in `services.py` immediately after receiving the adapter buffer and before `_persist_file`:

```python
# Rough sketch — confirm the exact ods-tools API against portfolios/models.py
from ods_tools.oed import OedExposure
oed = OedExposure.from_dataframes(location=_read_df(buf, fmt))
oed.check()   # raises OdsException on schema violation
buf.seek(0)
```

A clean ODS version mismatch should surface as a job `FAILED` with a descriptive `error_message`, not an unhandled 500.

### 2. Dummy GXM service integration tests

The adapter tests in `tests/adapters/test_gxm.py` are written and auto-skip when `OASIS_GXM_BASE_URL` is not set. They need the separate `dummy-gxm-service` container to be running. Once that repo is available:

```sh
OASIS_GXM_BASE_URL=http://localhost:8000 pytest src/server/oasisapi/external_providers/tests/adapters/
```

The dummy service must implement:
- `POST /v1/auth/token` → `{"access_token": "...", "expires_in": 3600}`
- `GET /v1/exposure/country/{iso2}?format=csv|parquet` → OED CSV or Parquet
- `GET /v1/exposure/bbox?bbox=...&format=...` → OED CSV or Parquet
- `POST /v1/exposure/lookup?fields=...&format=...` → OED CSV or Parquet with requested fields filled

### 3. Reset location_file_source on manual upload

When a user POSTs their own file to the existing `POST /portfolios/{id}/location_file/` endpoint, `location_file_source` should revert to `user_upload`. Currently the field keeps whatever value was last set by an external job.

Fix: override the `location_file` action in `PortfolioViewSet` (`portfolios/v2_api/viewsets.py`) to reset the three tracking fields after a successful upload:

```python
@extend_schema(responses={200: FILE_RESPONSE}, parameters=[FILE_FORMAT_PARAM])
@action(methods=['get', 'post', 'delete'], detail=True)
def location_file(self, request, pk=None, version=None):
    portfolio = self.get_object()
    response = handle_related_file(portfolio, 'location_file', request, self.supported_mime_types, ...)
    if request.method == 'POST' and response.status_code < 300:
        portfolio.refresh_from_db()
        portfolio.location_file_source = Portfolio.LocationFileSource.USER_UPLOAD
        portfolio.location_file_external_provider = ''
        portfolio.location_file_audit = None
        portfolio.save(update_fields=['location_file_source', 'location_file_external_provider', 'location_file_audit'])
    return response
```
