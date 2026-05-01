#!/usr/bin/env python3
"""
Oasis Platform API smoke-tester.

Reads the OpenAPI schema and exercises every endpoint, handling dependencies
(model → portfolio → location file → analysis → ...) automatically.

Usage:
    python test_api.py [options]

Options:
    --url           Base URL (default: http://localhost:8000)
    --schema        Path to OpenAPI JSON schema (default: v2-openapi-schema.json)
    --username      API username (default: admin)
    --password      API password (default: password)
    --no-cleanup    Keep created resources after the test run
    --v1            Also test v1 endpoints (default: v2 only)
    --verbose       Show full request/response details on failure
    --timeout       Request timeout in seconds (default: 30)
    --skip          Comma-separated list of operationIds to skip
"""

import argparse
import io
import json
import os
import sys
import textwrap
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import requests

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"
DIM = "\033[2m"


def c(color: str, text: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{color}{text}{RESET}"


# ---------------------------------------------------------------------------
# Minimal sample data
# ---------------------------------------------------------------------------
SAMPLE_LOCATION_CSV = textwrap.dedent("""\
    PortNumber,AccNumber,LocNumber,IsTenant,BuildingID,CountryCode,Latitude,Longitude,StreetAddress,PostalCode,OccupancyCode,ConstructionCode,LocPerilsCovered,BuildingTIV,OtherTIV,ContentsTIV,BITIV,LocCurrency,OEDVersion
    1,A11111,10002082046,1,1,GB,52.76698052,-0.895469856,1 ABINGDON ROAD,LE13 0HL,1050,5000,WW1,220000,0,0,0,GBP,latest version
    1,A11111,10002082047,1,1,GB,52.76697956,-0.89536613,2 ABINGDON ROAD,LE13 0HL,1050,5000,WW1,790000,0,0,0,GBP,latest version
""")

SAMPLE_ACCOUNTS_CSV = textwrap.dedent("""\
    PortNumber,AccNumber,AccCurrency,PolNumber,PolPerilsCovered,PolInceptionDate,PolExpiryDate,PolPeril,LayerNumber,LayerParticipation,LayerLimit,LayerAttachment,OEDVersion
    1,A11111,GBP,Layer1,WW1,2018-01-01,2018-12-31,WW1,1,0.3,5000000,500000,latest version
""")

SAMPLE_DATA_FILE_CONTENT = b"sample,data\n1,2\n"

SAMPLE_MODEL_SETTINGS = {
    "version": "3",
    "model_settings": {
        "event_set": {
            "name": "Event Set",
            "desc": "Piwind Event Set selection",
            "default": "p",
            "options": [{"id": "p", "desc": "Probabilistic", "number_of_events": 1447}],
        },
        "event_occurrence_id": {
            "name": "Occurrence Set",
            "desc": "PiWind Occurrence selection",
            "default": "lt",
            "options": [{"id": "lt", "desc": "Long Term"}],
        },
    },
    "lookup_settings": {
        "supported_perils": [
            {"id": "WSS", "desc": "Single Peril: Storm Surge", "peril_correlation_group": 1},
            {"id": "WTC", "desc": "Single Peril: Tropical Cyclone", "peril_correlation_group": 2},
            {"id": "WW1", "desc": "Group Peril: Windstorm with storm surge"},
            {"id": "WW2", "desc": "Group Peril: Windstorm w/o storm surge"},
        ]
    },
    "correlation_settings": [
        {"peril_correlation_group": 1, "damage_correlation_value": "0.7", "hazard_correlation_value": "0.0"},
        {"peril_correlation_group": 2, "damage_correlation_value": "0.5", "hazard_correlation_value": "0.0"},
    ],
    "data_settings": {
        "damage_group_fields": ["PortNumber", "AccNumber", "LocNumber"],
        "hazard_group_fields": ["PortNumber", "AccNumber", "LocNumber"],
    },
    "model_default_samples": 10,
}

SAMPLE_ANALYSIS_SETTINGS = {
        "version": "3",
        "analysis_tag": "ALL_outputs_tests",
        "source_tag": "MDK",
        "model_name_id": "PiWind",
        "model_supplier_id": "OasisLMF",
        "number_of_samples": 1,
        "gul_threshold": 0,
        "gul_output": True,
        "model_settings": {
            "event_set": "p",
            "event_occurrence_id": "lt",
        },
        "gul_summaries": [
            {
                "id": 1,
                "ord_output": {
                    "plt_sample": True, "plt_quantile": True, "plt_moment": True,
                    "elt_sample": True, "elt_quantile": True, "elt_moment": True,
                    "alt_period": True,
                    "ept_full_uncertainty_aep": True, "ept_full_uncertainty_oep": True,
                    "ept_mean_sample_aep": True, "ept_mean_sample_oep": True,
                    "ept_per_sample_mean_aep": True, "ept_per_sample_mean_oep": True,
                    "psept_aep": True, "psept_oep": True,
                    "parquet_format": False, "return_period_file": True,
                },
            }
        ],
        "il_output": True,
        "il_summaries": [
            {
                "id": 1,
                "ord_output": {
                    "plt_sample": True, "plt_quantile": True, "plt_moment": True,
                    "elt_sample": True, "elt_quantile": True, "elt_moment": True,
                    "alt_period": True,
                    "ept_full_uncertainty_aep": True, "ept_full_uncertainty_oep": True,
                    "ept_mean_sample_aep": True, "ept_mean_sample_oep": True,
                    "ept_per_sample_mean_aep": True, "ept_per_sample_mean_oep": True,
                    "psept_aep": True, "psept_oep": True,
                    "parquet_format": False, "return_period_file": True,
                },
            }
        ],
        "ri_output": True,
        "ri_summaries": [
            {
                "id": 1,
                "ord_output": {
                    "plt_sample": True, "plt_quantile": True, "plt_moment": True,
                    "elt_sample": True, "elt_quantile": True, "elt_moment": True,
                    "alt_period": True,
                    "ept_full_uncertainty_aep": True, "ept_full_uncertainty_oep": True,
                    "ept_mean_sample_aep": True, "ept_mean_sample_oep": True,
                    "ept_per_sample_mean_aep": True, "ept_per_sample_mean_oep": True,
                    "psept_aep": True, "psept_oep": True,
                    "parquet_format": False, "return_period_file": True,
                },
            }
        ],
        "rl_output": True,
        "rl_summaries": [
            {
                "id": 1,
                "ord_output": {
                    "plt_sample": True, "plt_quantile": True, "plt_moment": True,
                    "elt_sample": True, "elt_quantile": True, "elt_moment": True,
                    "alt_period": True,
                    "ept_full_uncertainty_aep": True, "ept_full_uncertainty_oep": True,
                    "ept_mean_sample_aep": True, "ept_mean_sample_oep": True,
                    "ept_per_sample_mean_aep": True, "ept_per_sample_mean_oep": True,
                    "psept_aep": True, "psept_oep": True,
                    "parquet_format": False, "return_period_file": True,
                },
            }
        ],
}


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------
@dataclass
class Result:
    operation_id: str
    method: str
    path: str
    status_code: Optional[int]
    passed: bool
    message: str
    duration_ms: float
    request_data: Any = None
    response_data: Any = None


@dataclass
class TestContext:
    """Stores IDs/objects created during the run so later tests can reference them."""
    token: Optional[str] = None
    model_id: Optional[int] = None
    portfolio_id: Optional[int] = None
    analysis_id: Optional[int] = None
    data_file_id: Optional[int] = None
    setting_template_id: Optional[int] = None
    task_status_id: Optional[int] = None
    results: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    created_models: list = field(default_factory=list)
    created_portfolios: list = field(default_factory=list)
    created_analyses: list = field(default_factory=list)
    created_data_files: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
class APIClient:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["Accept"] = "application/json"

    def set_token(self, token: str):
        self.session.headers["Authorization"] = f"Bearer {token}"

    def _url(self, path: str) -> str:
        return self.base_url + path

    def request(self, method: str, path: str, **kwargs) -> tuple[requests.Response, float]:
        url = self._url(path)
        kwargs.setdefault("timeout", self.timeout)
        t0 = time.monotonic()
        try:
            resp = self.session.request(method.upper(), url, **kwargs)
        except requests.RequestException as exc:
            raise
        duration_ms = (time.monotonic() - t0) * 1000
        return resp, duration_ms

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, **kw):
        return self.request("POST", path, **kw)

    def put(self, path, **kw):
        return self.request("PUT", path, **kw)

    def patch(self, path, **kw):
        return self.request("PATCH", path, **kw)

    def delete(self, path, **kw):
        return self.request("DELETE", path, **kw)


# ---------------------------------------------------------------------------
# Individual test helpers
# ---------------------------------------------------------------------------
def record(ctx: TestContext, op_id: str, method: str, path: str,
           resp: requests.Response, duration_ms: float,
           expect: list[int], verbose: bool,
           req_data: Any = None) -> bool:
    code = resp.status_code
    passed = code in expect
    try:
        rdata = resp.json()
    except Exception:
        rdata = resp.text[:200] if resp.text else None

    msg = f"HTTP {code}" + ("" if passed else f" (expected {expect})")
    result = Result(op_id, method.upper(), path, code, passed, msg, duration_ms, req_data, rdata)
    ctx.results.append(result)

    status = c(GREEN, "PASS") if passed else c(RED, "FAIL")
    print(f"  {status}  {c(DIM, method.upper())} {path}  {c(DIM, f'{duration_ms:.0f}ms')}  {msg}")
    if not passed or (verbose and code >= 400):
        if req_data is not None:
            print(f"        req:  {json.dumps(req_data, default=str)[:300]}")
        if rdata is not None:
            print(f"        resp: {json.dumps(rdata, default=str)[:300]}")
    return passed


def skip(ctx: TestContext, op_id: str, reason: str):
    ctx.skipped.append(op_id)
    print(f"  {c(YELLOW, 'SKIP')}  {op_id}  — {reason}")


# ---------------------------------------------------------------------------
# Ordered test suite
# ---------------------------------------------------------------------------
def run_tests(client: APIClient, ctx: TestContext, args: argparse.Namespace,
              schema: dict) -> None:
    v = args.verbose
    skip_ops = set(args.skip.split(",")) if args.skip else set()
    api = "/api"
    run_id = str(int(time.time()))

    # ------------------------------------------------------------------
    # 0. Auth
    # ------------------------------------------------------------------
    print(c(BOLD, "\n[Auth]"))
    creds = {"username": args.username, "password": args.password}
    resp, ms = client.post(f"{api}/access_token/", json=creds)
    if record(ctx, "access_token_create", "POST", f"{api}/access_token/",
              resp, ms, [200], v, creds):
        ctx.token = resp.json().get("access_token")
        client.set_token(ctx.token)
    else:
        print(c(RED, "\nAuthentication failed — cannot continue."))
        return

    # ------------------------------------------------------------------
    # 1. Read-only info endpoints
    # ------------------------------------------------------------------
    print(c(BOLD, "\n[Info / Health]"))
    for path in [
        f"{api}/healthcheck/",
        f"{api}/healthcheck_connections/",
        f"{api}/server_info/",
        f"{api}/oed_peril_codes/",
    ]:
        resp, ms = client.get(path)
        record(ctx, path, "GET", path, resp, ms, [200], v)

    # ------------------------------------------------------------------
    # 2. Data files (v2)
    # ------------------------------------------------------------------
    print(c(BOLD, "\n[Data Files — v2]"))
    resp, ms = client.get("/api/v2/data_files/")
    record(ctx, "v2_data_files_list", "GET", "/api/v2/data_files/", resp, ms, [200], v)

    # Create a data file (metadata only; content uploaded separately)
    resp, ms = client.post(
        "/api/v2/data_files/",
        data={"file_description": f"test-data-file-{run_id}"},
    )
    if record(ctx, "v2_data_files_create", "POST", "/api/v2/data_files/",
              resp, ms, [200, 201], v):
        ctx.data_file_id = resp.json().get("id")
        ctx.created_data_files.append(ctx.data_file_id)

    if ctx.data_file_id:
        dfid = ctx.data_file_id
        resp, ms = client.get(f"/api/v2/data_files/{dfid}/")
        record(ctx, "v2_data_files_retrieve", "GET", f"/api/v2/data_files/{dfid}/", resp, ms, [200], v)

        resp, ms = client.patch(f"/api/v2/data_files/{dfid}/", json={"file_description": "updated"})
        record(ctx, "v2_data_files_partial_update", "PATCH", f"/api/v2/data_files/{dfid}/", resp, ms, [200], v)

        # Upload content via the /content/ sub-endpoint
        file_bytes = io.BytesIO(SAMPLE_DATA_FILE_CONTENT)
        resp, ms = client.post(
            f"/api/v2/data_files/{dfid}/content/",
            files={"file": ("test.csv", file_bytes, "text/csv")},
        )
        record(ctx, "v2_data_files_content_create", "POST",
               f"/api/v2/data_files/{dfid}/content/", resp, ms, [200, 201], v)

        resp, ms = client.get(f"/api/v2/data_files/{dfid}/content/")
        record(ctx, "v2_data_files_content_retrieve", "GET", f"/api/v2/data_files/{dfid}/content/", resp, ms, [200], v)
    else:
        skip(ctx, "v2_data_files_*", "data file creation failed")

    # ------------------------------------------------------------------
    # 3. Models (v2)
    # ------------------------------------------------------------------
    print(c(BOLD, "\n[Models — v2]"))
    resp, ms = client.get("/api/v2/models/")
    record(ctx, "v2_models_list", "GET", "/api/v2/models/", resp, ms, [200], v)

    model_payload = {
        "supplier_id": "test-supplier",
        "model_id": "test-model",
        "version_id": f"test-{run_id}",
        "run_mode": "V2",
    }
    resp, ms = client.post("/api/v2/models/", json=model_payload)
    if record(ctx, "v2_models_create", "POST", "/api/v2/models/", resp, ms, [200, 201], v, model_payload):
        ctx.model_id = resp.json().get("id")
        ctx.created_models.append(ctx.model_id)

    if ctx.model_id:
        mid = ctx.model_id
        resp, ms = client.get(f"/api/v2/models/{mid}/")
        record(ctx, "v2_models_retrieve", "GET", f"/api/v2/models/{mid}/", resp, ms, [200], v)

        upd = {**model_payload, "version_id": f"test-{run_id}-upd"}
        resp, ms = client.put(f"/api/v2/models/{mid}/", json=upd)
        record(ctx, "v2_models_update", "PUT", f"/api/v2/models/{mid}/", resp, ms, [200], v, upd)

        resp, ms = client.patch(f"/api/v2/models/{mid}/", json={"version_id": f"test-{run_id}-pat"})
        record(ctx, "v2_models_partial_update", "PATCH", f"/api/v2/models/{mid}/", resp, ms, [200], v)

        resp, ms = client.get(f"/api/v2/models/{mid}/versions/")
        record(ctx, "v2_models_versions", "GET", f"/api/v2/models/{mid}/versions/", resp, ms, [200], v)

        resp, ms = client.get(f"/api/v2/models/{mid}/data_files/")
        record(ctx, "v2_models_data_files", "GET", f"/api/v2/models/{mid}/data_files/", resp, ms, [200], v)

        resp, ms = client.get(f"/api/v2/models/{mid}/settings/")
        record(ctx, "v2_models_settings_retrieve", "GET", f"/api/v2/models/{mid}/settings/", resp, ms, [200, 404], v)

        resp, ms = client.post(f"/api/v2/models/{mid}/settings/", json=SAMPLE_MODEL_SETTINGS)
        record(ctx, "v2_models_settings_create", "POST", f"/api/v2/models/{mid}/settings/",
               resp, ms, [200, 201], v, SAMPLE_MODEL_SETTINGS)

        resp, ms = client.get(f"/api/v2/models/{mid}/storage_links/")
        record(ctx, "v2_models_storage_links", "GET", f"/api/v2/models/{mid}/storage_links/", resp, ms, [200, 404], v)

        resp, ms = client.get(f"/api/v2/models/{mid}/chunking_configuration/")
        record(ctx, "v2_models_chunking_configuration_retrieve", "GET",
               f"/api/v2/models/{mid}/chunking_configuration/", resp, ms, [200], v)

        resp, ms = client.get(f"/api/v2/models/{mid}/scaling_configuration/")
        record(ctx, "v2_models_scaling_configuration_retrieve", "GET",
               f"/api/v2/models/{mid}/scaling_configuration/", resp, ms, [200], v)

        # Setting templates
        print(c(BOLD, "\n[Model Setting Templates — v2]"))
        resp, ms = client.get(f"/api/v2/models/{mid}/setting_templates/")
        record(ctx, "v2_models_setting_templates_list", "GET",
               f"/api/v2/models/{mid}/setting_templates/", resp, ms, [200], v)

        tmpl_payload = {"name": "test-template"}
        resp, ms = client.post(f"/api/v2/models/{mid}/setting_templates/", json=tmpl_payload)
        if record(ctx, "v2_models_setting_templates_create", "POST",
                  f"/api/v2/models/{mid}/setting_templates/", resp, ms, [200, 201], v, tmpl_payload):
            ctx.setting_template_id = resp.json().get("id")

        if ctx.setting_template_id:
            tid = ctx.setting_template_id
            resp, ms = client.get(f"/api/v2/models/{mid}/setting_templates/{tid}/")
            record(ctx, "v2_models_setting_templates_retrieve", "GET",
                   f"/api/v2/models/{mid}/setting_templates/{tid}/", resp, ms, [200], v)

            resp, ms = client.patch(f"/api/v2/models/{mid}/setting_templates/{tid}/",
                                    json={"name": "updated-template"})
            record(ctx, "v2_models_setting_templates_partial_update", "PATCH",
                   f"/api/v2/models/{mid}/setting_templates/{tid}/", resp, ms, [200], v)

            resp, ms = client.get(f"/api/v2/models/{mid}/setting_templates/{tid}/content/")
            record(ctx, "v2_models_setting_templates_content_retrieve", "GET",
                   f"/api/v2/models/{mid}/setting_templates/{tid}/content/", resp, ms, [200, 404], v)

            resp, ms = client.delete(f"/api/v2/models/{mid}/setting_templates/{tid}/")
            record(ctx, "v2_models_setting_templates_destroy", "DELETE",
                   f"/api/v2/models/{mid}/setting_templates/{tid}/", resp, ms, [200, 204], v)
    else:
        skip(ctx, "v2_models_*", "model creation failed")

    # ------------------------------------------------------------------
    # 4. Portfolios (v2)
    # ------------------------------------------------------------------
    print(c(BOLD, "\n[Portfolios — v2]"))
    resp, ms = client.get("/api/v2/portfolios/")
    record(ctx, "v2_portfolios_list", "GET", "/api/v2/portfolios/", resp, ms, [200], v)

    port_payload = {"name": "test-portfolio"}
    resp, ms = client.post("/api/v2/portfolios/", json=port_payload)
    if record(ctx, "v2_portfolios_create", "POST", "/api/v2/portfolios/", resp, ms, [200, 201], v, port_payload):
        ctx.portfolio_id = resp.json().get("id")
        ctx.created_portfolios.append(ctx.portfolio_id)

    if ctx.portfolio_id:
        pid = ctx.portfolio_id
        resp, ms = client.get(f"/api/v2/portfolios/{pid}/")
        record(ctx, "v2_portfolios_retrieve", "GET", f"/api/v2/portfolios/{pid}/", resp, ms, [200], v)

        upd = {"name": "test-portfolio-updated"}
        resp, ms = client.put(f"/api/v2/portfolios/{pid}/", json=upd)
        record(ctx, "v2_portfolios_update", "PUT", f"/api/v2/portfolios/{pid}/", resp, ms, [200], v, upd)

        resp, ms = client.patch(f"/api/v2/portfolios/{pid}/", json={"name": "test-portfolio-patched"})
        record(ctx, "v2_portfolios_partial_update", "PATCH", f"/api/v2/portfolios/{pid}/", resp, ms, [200], v)

        # Location file
        print(c(BOLD, "\n[Portfolio Files — v2]"))
        loc_file = io.BytesIO(SAMPLE_LOCATION_CSV.encode())
        resp, ms = client.post(
            f"/api/v2/portfolios/{pid}/location_file/",
            files={"file": ("location.csv", loc_file, "text/csv")},
        )
        record(ctx, "v2_portfolios_location_file_create", "POST",
               f"/api/v2/portfolios/{pid}/location_file/", resp, ms, [200, 201], v)

        resp, ms = client.get(f"/api/v2/portfolios/{pid}/location_file/")
        record(ctx, "v2_portfolios_location_file_retrieve", "GET",
               f"/api/v2/portfolios/{pid}/location_file/", resp, ms, [200], v)

        # Accounts file
        acc_file = io.BytesIO(SAMPLE_ACCOUNTS_CSV.encode())
        resp, ms = client.post(
            f"/api/v2/portfolios/{pid}/accounts_file/",
            files={"file": ("accounts.csv", acc_file, "text/csv")},
        )
        record(ctx, "v2_portfolios_accounts_file_create", "POST",
               f"/api/v2/portfolios/{pid}/accounts_file/", resp, ms, [200, 201], v)

        resp, ms = client.get(f"/api/v2/portfolios/{pid}/accounts_file/")
        record(ctx, "v2_portfolios_accounts_file_retrieve", "GET",
               f"/api/v2/portfolios/{pid}/accounts_file/", resp, ms, [200], v)

        # Validate portfolio
        resp, ms = client.get(f"/api/v2/portfolios/{pid}/validate/")
        record(ctx, "v2_portfolios_validate_retrieve", "GET",
               f"/api/v2/portfolios/{pid}/validate/", resp, ms, [200], v)

        # Reinsurance / currency files — not uploaded, so 404 is expected
        for file_ep in ["reinsurance_info_file", "reinsurance_scope_file", "currency_conversion_json",
                        "reporting_currency"]:
            resp, ms = client.get(f"/api/v2/portfolios/{pid}/{file_ep}/")
            record(ctx, f"v2_portfolios_{file_ep}_retrieve", "GET",
                   f"/api/v2/portfolios/{pid}/{file_ep}/", resp, ms, [200, 404], v)

        resp, ms = client.get(f"/api/v2/portfolios/{pid}/storage_links/")
        record(ctx, "v2_portfolios_storage_links_retrieve", "GET",
               f"/api/v2/portfolios/{pid}/storage_links/", resp, ms, [200, 404], v)

    else:
        skip(ctx, "v2_portfolios_*", "portfolio creation failed")

    # ------------------------------------------------------------------
    # 5. Analyses (v2) — direct creation
    # ------------------------------------------------------------------
    print(c(BOLD, "\n[Analyses — v2]"))
    resp, ms = client.get("/api/v2/analyses/")
    record(ctx, "v2_analyses_list", "GET", "/api/v2/analyses/", resp, ms, [200], v)

    if ctx.portfolio_id and ctx.model_id:
        analysis_payload = {
            "name": "test-analysis",
            "portfolio": ctx.portfolio_id,
            "model": ctx.model_id,
        }
        resp, ms = client.post("/api/v2/analyses/", json=analysis_payload)
        if record(ctx, "v2_analyses_create", "POST", "/api/v2/analyses/",
                  resp, ms, [200, 201], v, analysis_payload):
            ctx.analysis_id = resp.json().get("id")
            ctx.created_analyses.append(ctx.analysis_id)
    elif ctx.portfolio_id:
        # Try create_analysis via portfolio (no model required)
        ca_payload = {"name": "test-analysis-via-portfolio"}
        resp, ms = client.post(f"/api/v2/portfolios/{ctx.portfolio_id}/create_analysis/",
                               json=ca_payload)
        if record(ctx, "v2_portfolios_create_analysis", "POST",
                  f"/api/v2/portfolios/{ctx.portfolio_id}/create_analysis/",
                  resp, ms, [200, 201], v, ca_payload):
            ctx.analysis_id = resp.json().get("id")
            ctx.created_analyses.append(ctx.analysis_id)
    else:
        skip(ctx, "v2_analyses_create", "need portfolio and model")

    if ctx.portfolio_id and ctx.model_id:
        # Also test the portfolio create_analysis path
        ca_payload = {"name": "test-analysis-via-portfolio", "model": ctx.model_id}
        resp, ms = client.post(f"/api/v2/portfolios/{ctx.portfolio_id}/create_analysis/",
                               json=ca_payload)
        if record(ctx, "v2_portfolios_create_analysis", "POST",
                  f"/api/v2/portfolios/{ctx.portfolio_id}/create_analysis/",
                  resp, ms, [200, 201], v, ca_payload):
            extra_id = resp.json().get("id")
            if extra_id:
                ctx.created_analyses.append(extra_id)

    if ctx.analysis_id:
        aid = ctx.analysis_id

        resp, ms = client.get(f"/api/v2/analyses/{aid}/")
        record(ctx, "v2_analyses_retrieve", "GET", f"/api/v2/analyses/{aid}/", resp, ms, [200], v)

        upd_payload = {"name": "test-analysis-updated", "portfolio": ctx.portfolio_id, "model": ctx.model_id}
        resp, ms = client.put(f"/api/v2/analyses/{aid}/", json=upd_payload)
        record(ctx, "v2_analyses_update", "PUT", f"/api/v2/analyses/{aid}/", resp, ms, [200], v, upd_payload)

        resp, ms = client.patch(f"/api/v2/analyses/{aid}/", json={"name": "test-analysis-patched"})
        record(ctx, "v2_analyses_partial_update", "PATCH", f"/api/v2/analyses/{aid}/", resp, ms, [200], v)

        resp, ms = client.get(f"/api/v2/analyses/{aid}/run_progress/")
        record(ctx, "v2_analyses_run_progress", "GET", f"/api/v2/analyses/{aid}/run_progress/", resp, ms, [200], v)

        resp, ms = client.get(f"/api/v2/analyses/{aid}/data_files/")
        record(ctx, "v2_analyses_data_files", "GET", f"/api/v2/analyses/{aid}/data_files/", resp, ms, [200], v)

        resp, ms = client.get(f"/api/v2/analyses/{aid}/storage_links/")
        record(ctx, "v2_analyses_storage_links", "GET", f"/api/v2/analyses/{aid}/storage_links/", resp, ms, [200, 404], v)

        resp, ms = client.get(f"/api/v2/analyses/{aid}/chunking_configuration/")
        record(ctx, "v2_analyses_chunking_configuration_retrieve", "GET",
               f"/api/v2/analyses/{aid}/chunking_configuration/", resp, ms, [200], v)

        # Settings
        print(c(BOLD, "\n[Analysis Settings — v2]"))
        resp, ms = client.get(f"/api/v2/analyses/{aid}/settings/")
        record(ctx, "v2_analyses_settings_retrieve", "GET", f"/api/v2/analyses/{aid}/settings/", resp, ms, [200, 404], v)

        resp, ms = client.post(f"/api/v2/analyses/{aid}/settings/", json=SAMPLE_ANALYSIS_SETTINGS)
        record(ctx, "v2_analyses_settings_create", "POST", f"/api/v2/analyses/{aid}/settings/",
               resp, ms, [200, 201], v, SAMPLE_ANALYSIS_SETTINGS)

        # File endpoints that are expected empty (no run yet)
        print(c(BOLD, "\n[Analysis File Endpoints — v2 (pre-run, expect 200 or 404)]"))
        for file_ep in [
            "input_file", "output_file", "run_log_file",
            "input_generation_traceback_file", "run_traceback_file",
            "lookup_errors_file", "lookup_success_file", "lookup_validation_file",
            "summary_levels_file", "settings_file",
            "input_file_tar_list", "output_file_list", "output_file_tar_list",
            "sub_task_list",
        ]:
            resp, ms = client.get(f"/api/v2/analyses/{aid}/{file_ep}/")
            record(ctx, f"v2_analyses_{file_ep}_retrieve", "GET",
                   f"/api/v2/analyses/{aid}/{file_ep}/", resp, ms, [200, 400, 404], v)

        # Copy
        resp, ms = client.post(f"/api/v2/analyses/{aid}/copy/")
        if record(ctx, "v2_analyses_copy", "POST", f"/api/v2/analyses/{aid}/copy/",
                  resp, ms, [200, 201], v):
            copy_id = resp.json().get("id")
            if copy_id:
                ctx.created_analyses.append(copy_id)
    else:
        skip(ctx, "v2_analyses_*", "analysis creation failed")

    # ------------------------------------------------------------------
    # 6. Analysis Task Statuses (v2)
    # ------------------------------------------------------------------
    print(c(BOLD, "\n[Analysis Task Statuses — v2]"))
    resp, ms = client.get("/api/v2/analysis-task-statuses/")
    record(ctx, "v2_analysis_task_statuses_list", "GET", "/api/v2/analysis-task-statuses/", resp, ms, [200], v)

    # ------------------------------------------------------------------
    # 7. Queue endpoints (v2)
    # ------------------------------------------------------------------
    print(c(BOLD, "\n[Queue — v2]"))
    resp, ms = client.get("/api/v2/queue/")
    record(ctx, "v2_queue_retrieve", "GET", "/api/v2/queue/", resp, ms, [200], v)

    resp, ms = client.get("/api/v2/queue-status/")
    record(ctx, "v2_queue_status_retrieve", "GET", "/api/v2/queue-status/", resp, ms, [200], v)

    # ------------------------------------------------------------------
    # 8. v1 endpoints (optional)
    # ------------------------------------------------------------------
    if args.v1:
        print(c(BOLD, "\n[Models — v1]"))
        resp, ms = client.get("/api/v1/models/")
        record(ctx, "v1_models_list", "GET", "/api/v1/models/", resp, ms, [200], v)

        print(c(BOLD, "\n[Portfolios — v1]"))
        resp, ms = client.get("/api/v1/portfolios/")
        record(ctx, "v1_portfolios_list", "GET", "/api/v1/portfolios/", resp, ms, [200], v)

        print(c(BOLD, "\n[Analyses — v1]"))
        resp, ms = client.get("/api/v1/analyses/")
        record(ctx, "v1_analyses_list", "GET", "/api/v1/analyses/", resp, ms, [200], v)

        print(c(BOLD, "\n[Data Files — v1]"))
        resp, ms = client.get("/api/v1/data_files/")
        record(ctx, "v1_data_files_list", "GET", "/api/v1/data_files/", resp, ms, [200], v)

    # ------------------------------------------------------------------
    # 9. Endpoint coverage check against schema
    # ------------------------------------------------------------------
    _check_coverage(schema, ctx, args)


def _check_coverage(schema: dict, ctx: TestContext, args: argparse.Namespace):
    """Warn about schema paths that weren't exercised."""
    tested_paths = {(r.method, r.path) for r in ctx.results}
    skipped_ops = set(ctx.skipped)

    untested = []
    for path, methods in schema["paths"].items():
        for method, op in methods.items():
            op_id = op.get("operationId", "")
            # Skip OIDC, refresh token, and paths with complex param combos
            if any(x in path for x in ["/oidc/", "/refresh_token/", "output_file_sql",
                                        "tar_extract", "exposure_run", "exposure_transform",
                                        "generate_and_run", "generate_inputs", "cancel",
                                        "combine"]):
                continue
            # Normalise the path to see if it was tested
            normalised = path
            for param in ["{id}", "{models_pk}", "{file_pk}"]:
                normalised = normalised.replace(param, "*")
            tested = any(
                p.replace(str(ctx.model_id or ""), "*")
                 .replace(str(ctx.portfolio_id or ""), "*")
                 .replace(str(ctx.analysis_id or ""), "*")
                 .replace(str(ctx.data_file_id or ""), "*")
                == normalised.replace("{id}", "*").replace("{models_pk}", "*")
                for _, p in tested_paths
            )
            if not tested and op_id not in skipped_ops:
                untested.append((method.upper(), path, op_id))

    if untested:
        print(c(BOLD + YELLOW, f"\n[Coverage — {len(untested)} schema paths not exercised]"))
        for method, path, op_id in sorted(untested):
            print(f"  {c(DIM, method):<8} {path}  {c(DIM, op_id)}")


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
def cleanup(client: APIClient, ctx: TestContext):
    print(c(BOLD, "\n[Cleanup]"))
    deleted = 0

    for aid in ctx.created_analyses:
        try:
            resp, _ = client.delete(f"/api/v2/analyses/{aid}/")
            if resp.status_code in (200, 204):
                deleted += 1
            else:
                print(f"  {c(YELLOW, 'WARN')}  DELETE /api/v2/analyses/{aid}/ → {resp.status_code}")
        except Exception as e:
            print(f"  {c(YELLOW, 'WARN')}  Could not delete analysis {aid}: {e}")

    for pid in ctx.created_portfolios:
        try:
            resp, _ = client.delete(f"/api/v2/portfolios/{pid}/")
            if resp.status_code in (200, 204):
                deleted += 1
            else:
                print(f"  {c(YELLOW, 'WARN')}  DELETE /api/v2/portfolios/{pid}/ → {resp.status_code}")
        except Exception as e:
            print(f"  {c(YELLOW, 'WARN')}  Could not delete portfolio {pid}: {e}")

    for mid in ctx.created_models:
        try:
            resp, _ = client.delete(f"/api/v2/models/{mid}/")
            if resp.status_code in (200, 204):
                deleted += 1
            else:
                print(f"  {c(YELLOW, 'WARN')}  DELETE /api/v2/models/{mid}/ → {resp.status_code}")
        except Exception as e:
            print(f"  {c(YELLOW, 'WARN')}  Could not delete model {mid}: {e}")

    for dfid in ctx.created_data_files:
        try:
            resp, _ = client.delete(f"/api/v2/data_files/{dfid}/")
            if resp.status_code in (200, 204):
                deleted += 1
            else:
                print(f"  {c(YELLOW, 'WARN')}  DELETE /api/v2/data_files/{dfid}/ → {resp.status_code}")
        except Exception as e:
            print(f"  {c(YELLOW, 'WARN')}  Could not delete data file {dfid}: {e}")

    print(f"  Deleted {deleted} resource(s)")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
def print_summary(ctx: TestContext):
    total = len(ctx.results)
    passed = sum(1 for r in ctx.results if r.passed)
    failed = total - passed
    skipped = len(ctx.skipped)

    print(c(BOLD, "\n" + "=" * 60))
    print(c(BOLD, "RESULTS"))
    print("=" * 60)
    print(f"  Total:   {total}")
    print(f"  {c(GREEN, 'Passed')}: {passed}")
    if failed:
        print(f"  {c(RED, 'Failed')}: {failed}")
    if skipped:
        print(f"  {c(YELLOW, 'Skipped')}: {skipped}")

    if failed:
        print(c(BOLD + RED, "\nFailed tests:"))
        for r in ctx.results:
            if not r.passed:
                print(f"  {r.method} {r.path} → {r.message}")
                if r.response_data:
                    snippet = json.dumps(r.response_data, default=str)[:200]
                    print(f"    {c(DIM, snippet)}")

    slow = sorted([r for r in ctx.results], key=lambda r: r.duration_ms, reverse=True)[:5]
    print(c(BOLD, "\nSlowest requests:"))
    for r in slow:
        status = c(GREEN, "ok") if r.passed else c(RED, "fail")
        print(f"  {r.duration_ms:>8.0f}ms  {r.method} {r.path}  [{status}]")

    print()
    return failed == 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Oasis Platform API smoke-tester")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL")
    parser.add_argument("--schema", default="v2-openapi-schema.json", help="Path to OpenAPI JSON schema")
    parser.add_argument("--username", default="admin", help="API username")
    parser.add_argument("--password", default="password", help="API password")
    parser.add_argument("--no-cleanup", action="store_true", help="Keep created resources")
    parser.add_argument("--v1", action="store_true", help="Also test v1 endpoints")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show request/response on failure")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    parser.add_argument("--skip", default="", help="Comma-separated operationIds to skip")
    args = parser.parse_args()

    # Load schema
    schema_path = args.schema
    if not os.path.isabs(schema_path):
        schema_path = os.path.join(os.getcwd(), schema_path)
    if not os.path.exists(schema_path):
        print(c(RED, f"Schema file not found: {schema_path}"))
        print("Generate it with: python ./manage.py spectacular --format openapi-json --file v2-openapi-schema.json")
        sys.exit(1)

    with open(schema_path) as f:
        schema = json.load(f)

    print(c(BOLD, f"Oasis Platform API Tester"))
    print(f"  URL:    {args.url}")
    print(f"  Schema: {schema_path}  ({len(schema['paths'])} paths)")
    print(f"  User:   {args.username}")

    client = APIClient(args.url, timeout=args.timeout)
    ctx = TestContext()

    try:
        run_tests(client, ctx, args, schema)
    except KeyboardInterrupt:
        print(c(YELLOW, "\nInterrupted"))
    finally:
        if not args.no_cleanup and ctx.token:
            cleanup(client, ctx)

    success = print_summary(ctx)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
