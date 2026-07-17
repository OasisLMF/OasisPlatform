"""
Integration tests for GXMAdapter against the dummy GXM service.

Run these with the dummy service up:
    docker compose -f <dummy-gxm-service>/docker-compose.yml up -d

Set OASIS_GXM_BASE_URL (and optionally OASIS_GXM_CLIENT_ID / OASIS_GXM_CLIENT_SECRET)
in your environment or conf.ini. Tests are skipped automatically when OASIS_GXM_BASE_URL
is not set.
"""
import io
import os

import pytest

SKIP_REASON = 'OASIS_GXM_BASE_URL not set; start the dummy GXM service and set this env var'
GXM_BASE_URL = os.environ.get('OASIS_GXM_BASE_URL', '')
requires_dummy_gxm = pytest.mark.skipif(not GXM_BASE_URL, reason=SKIP_REASON)


def _make_settings():
    class _S:
        base_url = GXM_BASE_URL
        client_id = os.environ.get('OASIS_GXM_CLIENT_ID', 'oasis-dev')
        client_secret = os.environ.get('OASIS_GXM_CLIENT_SECRET', 'not-a-real-secret')
        default_as_of = None
    return _S()


@requires_dummy_gxm
def test_get_token_returns_string():
    from src.server.oasisapi.external_providers.adapters.gxm import GXMAdapter
    adapter = GXMAdapter(_make_settings())
    token = adapter.get_token()
    assert isinstance(token, str)
    assert len(token) > 0


@requires_dummy_gxm
def test_get_token_cached():
    from src.server.oasisapi.external_providers.adapters.gxm import GXMAdapter
    adapter = GXMAdapter(_make_settings())
    t1 = adapter.get_token()
    t2 = adapter.get_token()
    assert t1 == t2  # second call returns cached token


@requires_dummy_gxm
def test_fetch_country_csv_returns_bytes():
    from src.server.oasisapi.external_providers.adapters.gxm import GXMAdapter
    adapter = GXMAdapter(_make_settings())
    buf = adapter.fetch_country('GH', format='csv')
    assert isinstance(buf, io.BytesIO)
    content = buf.read()
    assert len(content) > 0


@requires_dummy_gxm
def test_fetch_country_parquet_returns_parseable_data():
    import pandas as pd
    from src.server.oasisapi.external_providers.adapters.gxm import GXMAdapter
    adapter = GXMAdapter(_make_settings())
    buf = adapter.fetch_country('GH', format='parquet')
    buf.seek(0)
    df = pd.read_parquet(buf)
    assert len(df) > 0
    assert 'Latitude' in df.columns
    assert 'Longitude' in df.columns


@requires_dummy_gxm
def test_fetch_bbox_returns_data():
    from src.server.oasisapi.external_providers.adapters.gxm import GXMAdapter
    adapter = GXMAdapter(_make_settings())
    buf = adapter.fetch_bbox([-1.35, 5.50, -0.05, 6.05], format='csv')
    content = buf.read()
    assert len(content) > 0


@requires_dummy_gxm
def test_lookup_enriches_fields():
    import pandas as pd
    from src.server.oasisapi.external_providers.adapters.gxm import GXMAdapter
    adapter = GXMAdapter(_make_settings())
    input_csv = b'PortNumber,AccNumber,LocNumber,Latitude,Longitude\n1,A,L1,5.6,0.2\n'
    result_buf = adapter.lookup(
        io.BytesIO(input_csv),
        fields=['OccupancyCode'],
        input_format='csv',
        output_format='csv',
    )
    result_buf.seek(0)
    df = pd.read_csv(result_buf)
    assert 'OccupancyCode' in df.columns
    assert len(df) == 1
