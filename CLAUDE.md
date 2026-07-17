# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Oasis Platform is a Django/Celery-based platform for managing and executing catastrophe insurance risk models. It exposes a REST API for portfolio and analysis management, and a distributed Celery worker system that executes the actual model computations via the `oasislmf` library.

## Commands

### Development Setup
```bash
pip install pip-tools
pip-compile          # Regenerate requirements.txt from .in files
pip-sync             # Install/sync all dependencies
python manage.py migrate
python manage.py createsuperuser
```

### Running Tests
```bash
# All tests (Django settings auto-configured via setup.cfg)
pytest

# Specific file or test
pytest src/server/oasisapi/portfolios/v2_api/tests/test_portfolio.py
pytest src/server/oasisapi/portfolios/v2_api/tests/test_portfolio.py::PortfolioDetailViewTestCase::test_user_is_not_authenticated___response_is_forbidden

# With coverage
pytest --cov=src src/server/oasisapi/

# OIDC/Keycloak tests (excluded by default — need different Django config)
OASIS_API_AUTH_TYPE=keycloak pytest src/server/oasisapi/auth/tests/test_oidc.py

# Full test suite via tox
tox
```

### Linting
```bash
flake8 src/
```

### Database
```bash
python manage.py makemigrations
python manage.py migrate
```

### Docker (local full stack)
```bash
docker-compose up -d
curl localhost:8000/healthcheck
```

## Architecture

The platform has three main runtime components:

### 1. Django API Server (`src/server/oasisapi/`)
REST API built with Django 5.2 + Django REST Framework. Key apps:
- `portfolios` — insurance portfolio management
- `analyses` — analysis lifecycle (create, run, retrieve results)
- `analysis_models` — risk model registry
- `data_files` / `files` — file upload and storage
- `auth` / `oidc` — authentication (standard JWT or Keycloak/OIDC)
- `queues` — Celery queue introspection
- `combine` — result aggregation
- `external_providers` — GXM / external exposure-data integration (feature-flagged, phase 1)

**Dual API versions**: V1 (legacy) and V2 (current) coexist under the same Django project. Settings modules for each are at `src/server/oasisapi/settings/v1.py` and `v2.py`, both inheriting from `base.py`.

Entry: `wsgi/` (Gunicorn/HTTP) and `asgi/` (Daphne/WebSocket via Django Channels + Redis).

### 2. Celery Worker (`src/model_execution_worker/`)
Executes model runs as async tasks. Key files:
- `tasks.py` — main model execution tasks
- `distributed_tasks.py` — parallel/distributed execution
- `server_tasks.py` — background server-initiated tasks
- `celery_app_v1.py` / `celery_app_v2.py` — Celery app definitions for each API version

Broker: RabbitMQ (default) or Redis (`OASIS_CELERY_BROKER_URL`). Workers call `oasislmf` to run the insurance model kernel.

### 3. Kubernetes Worker Controller (`kubernetes/`)
Optionally autoscales worker pods based on Celery queue depth. See `kubernetes/README.md`.

## Configuration

Primary config is `conf.ini` (INI format) with environment variable overrides. Key sections:
- `[server]` — Django secret key, debug, auth type, storage backend
- `[worker]` — model registry, storage, numba warmup
- `[celery]` — broker URL, result backend

Common env vars:
| Variable | Purpose |
|---|---|
| `OASIS_DEBUG` | Enable debug mode |
| `OASIS_CELERY_BROKER_URL` | RabbitMQ or Redis URL |
| `OASIS_SERVER_DB_*` | API server database credentials |
| `OASIS_CELERY_DB_*` | Celery result backend credentials |
| `OASIS_API_AUTH_TYPE` | Set to `keycloak` for OIDC |
| `OASIS_STORAGE_TYPE` | `local`, `aws-s3`, or `azure` |
| `DJANGO_SETTINGS_MODULE` | Override the settings module |

Config parser: `src/conf/iniconf.py`. Django settings: `src/server/oasisapi/settings/base.py`.

## Key Conventions

**Test settings**: `DJANGO_SETTINGS_MODULE=src.server.oasisapi.settings` is set automatically in `setup.cfg`. Tests use a fast custom password hasher to speed up auth-related tests.

**File storage**: Abstracted via `oasis-data-manager`. All file operations go through the storage layer — never write to disk directly in application code.

**API workflow**: Portfolio → upload exposure files → create Analysis → attach settings file → run Analysis → Celery executes model → poll for results.

**Data format**: Primary exposure format is ODS (Oasis Data Standard), handled by `ods-tools`.

**Migrations**: Never skip `python manage.py migrate` after pulling. The CI runs `test-db-migration.yml` to validate migration history.

**Requirements**: Edit `.in` files and run `pip-compile` to update locked `.txt` files. Three sets: `requirements-server.*`, `requirements-worker.*`, `requirements.*` (combined dev).

## External Providers (GXM integration, `feature/gxm-adapter` branch)

Gate: `EXTERNAL_PROVIDERS_ENABLED=1` in `[server]` conf.ini (or env var). Off by default — zero change to existing behaviour when off.

New endpoints under `/api/v2/providers/{provider}/portfolios/{id}/`:
- `POST external_location_file/` — UC1: fetch OED file from provider → 202 + job_id
- `POST external_enrich/` — UC2: fill missing OED fields → 202 + job_id
- `GET external_jobs/{job_id}/` — poll job status and result URL

Admin-only: `GET/PUT /api/v2/external_provider_settings/{provider}/`

Dev loop env vars: `OASIS_GXM_BASE_URL`, `OASIS_GXM_CLIENT_ID`, `OASIS_GXM_CLIENT_SECRET`.

Source layout: `src/server/oasisapi/external_providers/` — `models.py`, `services.py`, `tasks.py`, `views.py`, `urls.py`, `adapters/{base,gxm}.py`, `tests/`.

Portfolio serializer: `location_file` response gains `source` (user_upload/external/merged), `external_provider`, `audit_url` — additive, backward compatible.
