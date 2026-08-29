import io
import pytest
from unittest.mock import MagicMock, patch

from src.server.oasisapi.external_providers.models import ExternalJob
from src.server.oasisapi.external_providers.services import (
    _is_blank,
    _merge_non_destructive,
    run_enrich,
    run_location_file,
)

SAMPLE_CSV = b'PortNumber,AccNumber,LocNumber,CountryCode,Latitude,Longitude,OccupancyCode\n1,ACC1,LOC1,GH,5.6,0.2,\n1,ACC1,LOC2,GH,5.7,0.3,9999\n'
ENRICHED_CSV = b'PortNumber,AccNumber,LocNumber,CountryCode,Latitude,Longitude,OccupancyCode\n1,ACC1,LOC1,GH,5.6,0.2,1100\n1,ACC1,LOC2,GH,5.7,0.3,2200\n'


# ---------------------------------------------------------------------------
# _is_blank
# ---------------------------------------------------------------------------

def test_is_blank_none():
    assert _is_blank(None)


def test_is_blank_empty_string():
    assert _is_blank('')
    assert _is_blank('  ')


def test_is_blank_nan():
    assert _is_blank(float('nan'))


def test_is_blank_value():
    assert not _is_blank(1100)
    assert not _is_blank('residential')


# ---------------------------------------------------------------------------
# _merge_non_destructive
# ---------------------------------------------------------------------------

def test_merge_fills_blank_fields():
    orig = io.BytesIO(SAMPLE_CSV)
    enriched = io.BytesIO(ENRICHED_CSV)
    merged_buf, audit = _merge_non_destructive(orig, enriched, ['OccupancyCode'], 'csv', 'csv')

    import pandas as pd
    merged_buf.seek(0)
    df = pd.read_csv(merged_buf)

    # LOC1 was blank → should be filled
    assert df.loc[df['LocNumber'] == 'LOC1', 'OccupancyCode'].values[0] == 1100
    # LOC2 had a value → should NOT be overwritten
    assert df.loc[df['LocNumber'] == 'LOC2', 'OccupancyCode'].values[0] == 9999

    assert 'OccupancyCode' in audit
    assert 0 in audit['OccupancyCode']['filled_row_indices']
    assert 1 not in audit['OccupancyCode']['filled_row_indices']


def test_merge_empty_audit_when_all_filled():
    already_filled = b'PortNumber,AccNumber,LocNumber,Latitude,Longitude,OccupancyCode\n1,A,L1,5.6,0.2,1100\n'
    orig = io.BytesIO(already_filled)
    enriched = io.BytesIO(already_filled)
    _, audit = _merge_non_destructive(orig, enriched, ['OccupancyCode'], 'csv', 'csv')
    assert audit == {}


# ---------------------------------------------------------------------------
# run_location_file
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_run_location_file_completes(pending_location_job, user, provider_settings):
    mock_buf = io.BytesIO(SAMPLE_CSV)
    mock_adapter = MagicMock()
    mock_adapter.fetch_country.return_value = mock_buf

    with patch('src.server.oasisapi.external_providers.services.get_adapter', return_value=mock_adapter), \
         patch('src.server.oasisapi.external_providers.services.get_provider_settings', return_value=provider_settings):
        run_location_file(str(pending_location_job.id), user.pk)

    pending_location_job.refresh_from_db()
    assert pending_location_job.status == ExternalJob.Status.COMPLETED
    assert pending_location_job.result_file is not None
    assert pending_location_job.portfolio.location_file is not None
    assert pending_location_job.portfolio.location_file_source == 'external'
    assert pending_location_job.portfolio.location_file_external_provider == 'gxm'


@pytest.mark.django_db
def test_run_location_file_with_bbox(pending_location_job, user, provider_settings):
    pending_location_job.request_data = {
        'country_code': 'GH',
        'format': 'csv',
        'filters': {'bbox': [-1.35, 5.50, -0.05, 6.05]},
    }
    pending_location_job.save()

    mock_buf = io.BytesIO(SAMPLE_CSV)
    mock_adapter = MagicMock()
    mock_adapter.fetch_bbox.return_value = mock_buf

    with patch('src.server.oasisapi.external_providers.services.get_adapter', return_value=mock_adapter), \
         patch('src.server.oasisapi.external_providers.services.get_provider_settings', return_value=provider_settings):
        run_location_file(str(pending_location_job.id), user.pk)

    mock_adapter.fetch_bbox.assert_called_once()
    call_args = mock_adapter.fetch_bbox.call_args
    assert call_args[0][0] == [-1.35, 5.50, -0.05, 6.05]


@pytest.mark.django_db
def test_run_location_file_marks_failed_on_error(pending_location_job, user, provider_settings):
    mock_adapter = MagicMock()
    mock_adapter.fetch_country.side_effect = RuntimeError('GXM unavailable')

    with patch('src.server.oasisapi.external_providers.services.get_adapter', return_value=mock_adapter), \
         patch('src.server.oasisapi.external_providers.services.get_provider_settings', return_value=provider_settings), \
         pytest.raises(RuntimeError):
        run_location_file(str(pending_location_job.id), user.pk)

    pending_location_job.refresh_from_db()
    assert pending_location_job.status == ExternalJob.Status.FAILED
    assert 'GXM unavailable' in pending_location_job.error_message


# ---------------------------------------------------------------------------
# run_enrich
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_run_enrich_non_destructive(pending_enrich_job, user, provider_settings):
    mock_buf = io.BytesIO(ENRICHED_CSV)
    mock_adapter = MagicMock()
    mock_adapter.lookup.return_value = mock_buf

    with patch('src.server.oasisapi.external_providers.services.get_adapter', return_value=mock_adapter), \
         patch('src.server.oasisapi.external_providers.services.get_provider_settings', return_value=provider_settings):
        run_enrich(str(pending_enrich_job.id), user.pk)

    pending_enrich_job.refresh_from_db()
    assert pending_enrich_job.status == ExternalJob.Status.COMPLETED
    assert pending_enrich_job.result_file is not None
    assert pending_enrich_job.audit_file is not None
    portfolio = pending_enrich_job.portfolio
    assert portfolio.location_file_source == 'merged'


@pytest.mark.django_db
def test_run_enrich_with_overwrite_produces_no_audit(pending_enrich_job, user, provider_settings):
    pending_enrich_job.request_data['overwrite'] = True
    pending_enrich_job.save()

    mock_buf = io.BytesIO(ENRICHED_CSV)
    mock_adapter = MagicMock()
    mock_adapter.lookup.return_value = mock_buf

    with patch('src.server.oasisapi.external_providers.services.get_adapter', return_value=mock_adapter), \
         patch('src.server.oasisapi.external_providers.services.get_provider_settings', return_value=provider_settings):
        run_enrich(str(pending_enrich_job.id), user.pk)

    pending_enrich_job.refresh_from_db()
    assert pending_enrich_job.status == ExternalJob.Status.COMPLETED
    assert pending_enrich_job.audit_file is None


@pytest.mark.django_db
def test_run_enrich_no_location_file_fails(pending_enrich_job, user, provider_settings):
    pending_enrich_job.portfolio.location_file = None
    pending_enrich_job.portfolio.save()

    with patch('src.server.oasisapi.external_providers.services.get_provider_settings', return_value=provider_settings), \
         pytest.raises(ValueError, match='no location file'):
        run_enrich(str(pending_enrich_job.id), user.pk)

    pending_enrich_job.refresh_from_db()
    assert pending_enrich_job.status == ExternalJob.Status.FAILED
