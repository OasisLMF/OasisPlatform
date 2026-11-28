import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from src.server.oasisapi.external_providers.models import ExternalJob

BASE = '/v2'
PROVIDERS_BASE = f'{BASE}/providers/gxm/portfolios'


def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ---------------------------------------------------------------------------
# Feature flag off → all endpoints return 404
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@override_settings(EXTERNAL_PROVIDERS_ENABLED=False)
def test_flag_off_location_file_returns_404(portfolio, user):
    client = authed_client(user)
    resp = client.post(f'{PROVIDERS_BASE}/{portfolio.pk}/external_location_file/', {'country_code': 'GH'}, format='json')
    assert resp.status_code == 404


@pytest.mark.django_db
@override_settings(EXTERNAL_PROVIDERS_ENABLED=False)
def test_flag_off_enrich_returns_404(portfolio, user):
    client = authed_client(user)
    resp = client.post(f'{PROVIDERS_BASE}/{portfolio.pk}/external_enrich/', {'fields': ['OccupancyCode']}, format='json')
    assert resp.status_code == 404


@pytest.mark.django_db
@override_settings(EXTERNAL_PROVIDERS_ENABLED=False)
def test_flag_off_job_detail_returns_404(portfolio, user):
    client = authed_client(user)
    resp = client.get(f'{PROVIDERS_BASE}/{portfolio.pk}/external_jobs/00000000-0000-0000-0000-000000000001/')
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Unknown provider → 404
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@override_settings(EXTERNAL_PROVIDERS_ENABLED=True)
def test_unknown_provider_returns_404(portfolio, user):
    client = authed_client(user)
    resp = client.post(
        f'{BASE}/providers/notreal/portfolios/{portfolio.pk}/external_location_file/',
        {'country_code': 'GH'},
        format='json',
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Unauthenticated requests → 401
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@override_settings(EXTERNAL_PROVIDERS_ENABLED=True)
def test_unauthenticated_location_file_returns_401(portfolio):
    client = APIClient()
    resp = client.post(f'{PROVIDERS_BASE}/{portfolio.pk}/external_location_file/', {'country_code': 'GH'}, format='json')
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# UC1 — POST external_location_file → 202
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@override_settings(EXTERNAL_PROVIDERS_ENABLED=True)
def test_post_location_file_returns_202(portfolio, user, provider_settings, mocker):
    mocker.patch('src.server.oasisapi.external_providers.tasks.run_external_location_file_task.apply_async')
    client = authed_client(user)
    resp = client.post(
        f'{PROVIDERS_BASE}/{portfolio.pk}/external_location_file/',
        {'country_code': 'GH', 'format': 'csv'},
        format='json',
    )
    assert resp.status_code == 202
    data = resp.json()
    assert 'job_id' in data
    assert data['status'] == 'PENDING'
    assert 'status_url' in data


@pytest.mark.django_db
@override_settings(EXTERNAL_PROVIDERS_ENABLED=True)
def test_post_location_file_creates_job_record(portfolio, user, provider_settings, mocker):
    mocker.patch('src.server.oasisapi.external_providers.tasks.run_external_location_file_task.apply_async')
    client = authed_client(user)
    client.post(
        f'{PROVIDERS_BASE}/{portfolio.pk}/external_location_file/',
        {'country_code': 'GH', 'format': 'parquet'},
        format='json',
    )
    job = ExternalJob.objects.get(portfolio=portfolio, job_type='location_file')
    assert job.provider == 'gxm'
    assert job.request_data['country_code'] == 'GH'
    assert job.request_data['format'] == 'parquet'


@pytest.mark.django_db
@override_settings(EXTERNAL_PROVIDERS_ENABLED=True)
def test_post_location_file_dispatches_celery_task(portfolio, user, provider_settings, mocker):
    mock_apply = mocker.patch(
        'src.server.oasisapi.external_providers.tasks.run_external_location_file_task.apply_async'
    )
    mock_apply.return_value.id = 'fake-task-id'
    client = authed_client(user)
    client.post(
        f'{PROVIDERS_BASE}/{portfolio.pk}/external_location_file/',
        {'country_code': 'GH'},
        format='json',
    )
    assert mock_apply.called
    _, kwargs = mock_apply.call_args
    assert kwargs['queue'] == 'oasis-internal-worker'


# ---------------------------------------------------------------------------
# Bbox serializer validation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@override_settings(EXTERNAL_PROVIDERS_ENABLED=True)
def test_location_file_bbox_wrong_length(portfolio, user, provider_settings, mocker):
    mocker.patch('src.server.oasisapi.external_providers.tasks.run_external_location_file_task.apply_async')
    client = authed_client(user)
    resp = client.post(
        f'{PROVIDERS_BASE}/{portfolio.pk}/external_location_file/',
        {'country_code': 'GH', 'filters': {'bbox': [1.0, 2.0]}},
        format='json',
    )
    assert resp.status_code == 400


@pytest.mark.django_db
@override_settings(EXTERNAL_PROVIDERS_ENABLED=True)
def test_location_file_antimeridian_bbox_rejected(portfolio, user, provider_settings, mocker):
    mocker.patch('src.server.oasisapi.external_providers.tasks.run_external_location_file_task.apply_async')
    client = authed_client(user)
    resp = client.post(
        f'{PROVIDERS_BASE}/{portfolio.pk}/external_location_file/',
        {'country_code': 'FJ', 'filters': {'bbox': [170.0, -20.0, -175.0, -15.0]}},
        format='json',
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# UC2 — POST external_enrich → 202
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@override_settings(EXTERNAL_PROVIDERS_ENABLED=True)
def test_post_enrich_no_location_file_returns_400(portfolio, user, provider_settings):
    client = authed_client(user)
    resp = client.post(
        f'{PROVIDERS_BASE}/{portfolio.pk}/external_enrich/',
        {'fields': ['OccupancyCode']},
        format='json',
    )
    assert resp.status_code == 400


@pytest.mark.django_db
@override_settings(EXTERNAL_PROVIDERS_ENABLED=True)
def test_post_enrich_returns_202(portfolio_with_file, user, provider_settings, mocker):
    mocker.patch('src.server.oasisapi.external_providers.tasks.run_external_enrich_task.apply_async')
    client = authed_client(user)
    resp = client.post(
        f'{PROVIDERS_BASE}/{portfolio_with_file.pk}/external_enrich/',
        {'fields': ['OccupancyCode', 'ConstructionCode'], 'overwrite': False},
        format='json',
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data['status'] == 'PENDING'


# ---------------------------------------------------------------------------
# Job polling
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@override_settings(EXTERNAL_PROVIDERS_ENABLED=True)
def test_get_job_detail(pending_location_job, user):
    client = authed_client(user)
    resp = client.get(f'{PROVIDERS_BASE}/{pending_location_job.portfolio_id}/external_jobs/{pending_location_job.id}/')
    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'PENDING'
    assert 'status_url' in data


@pytest.mark.django_db
@override_settings(EXTERNAL_PROVIDERS_ENABLED=True)
def test_get_job_detail_wrong_portfolio_404(pending_location_job, user, portfolio_with_file):
    client = authed_client(user)
    resp = client.get(f'{PROVIDERS_BASE}/{portfolio_with_file.pk}/external_jobs/{pending_location_job.id}/')
    assert resp.status_code == 404


@pytest.mark.django_db
@override_settings(EXTERNAL_PROVIDERS_ENABLED=True)
def test_list_jobs(pending_location_job, user):
    client = authed_client(user)
    resp = client.get(f'{PROVIDERS_BASE}/{pending_location_job.portfolio_id}/external_jobs/')
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ---------------------------------------------------------------------------
# Admin settings endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@override_settings(EXTERNAL_PROVIDERS_ENABLED=True)
def test_non_admin_cannot_get_provider_settings(user):
    client = authed_client(user)
    resp = client.get(f'{BASE}/external_provider_settings/gxm/')
    assert resp.status_code == 403


@pytest.mark.django_db
@override_settings(EXTERNAL_PROVIDERS_ENABLED=True)
def test_admin_can_get_provider_settings(admin_user, provider_settings):
    client = authed_client(admin_user)
    resp = client.get(f'{BASE}/external_provider_settings/gxm/')
    assert resp.status_code == 200
    data = resp.json()
    assert data['provider'] == 'gxm'
    assert 'client_secret' not in data  # write-only


@pytest.mark.django_db
@override_settings(EXTERNAL_PROVIDERS_ENABLED=True)
def test_admin_can_put_provider_settings(admin_user):
    client = authed_client(admin_user)
    resp = client.put(
        f'{BASE}/external_provider_settings/gxm/',
        {'base_url': 'https://api.gxm.example', 'client_id': 'oasis', 'client_secret': 'secret'},
        format='json',
    )
    assert resp.status_code == 200
    assert resp.json()['base_url'] == 'https://api.gxm.example'


# ---------------------------------------------------------------------------
# Portfolio location_file backward-compatibility regression
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@override_settings(EXTERNAL_PROVIDERS_ENABLED=False)
def test_portfolio_location_file_response_has_source_field(portfolio_with_file, user):
    """Existing callers that ignore new fields must see no breaking change."""
    client = authed_client(user)
    resp = client.get(f'{BASE}/portfolios/{portfolio_with_file.pk}/')
    assert resp.status_code == 200
    data = resp.json()
    loc = data['location_file']
    assert loc is not None
    assert loc['source'] == 'user_upload'
    assert loc['external_provider'] == ''
    assert loc['audit_url'] is None
