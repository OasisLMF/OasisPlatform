import io
import logging
import threading
import time
from typing import Literal, Optional

import requests

from .base import ExposureProvider

logger = logging.getLogger(__name__)

_token_lock = threading.Lock()


class GXMAdapter(ExposureProvider):
    def __init__(self, provider_settings):
        self._settings = provider_settings
        self._token: Optional[str] = None
        self._token_expiry: float = 0.0

    def _base_url(self) -> str:
        return self._settings.base_url.rstrip('/')

    def get_token(self) -> str:
        with _token_lock:
            if self._token and time.time() < self._token_expiry - 30:
                return self._token
            resp = requests.post(
                f'{self._base_url()}/v1/auth/token',
                data={
                    'grant_type': 'client_credentials',
                    'client_id': self._settings.client_id,
                    'client_secret': self._settings.client_secret,
                    'scope': 'exposure.read',
                },
                timeout=30,
            )
            resp.raise_for_status()
            payload = resp.json()
            self._token = payload['access_token']
            self._token_expiry = time.time() + payload.get('expires_in', 3600)
            return self._token

    def _auth_headers(self) -> dict:
        return {'Authorization': f'Bearer {self.get_token()}'}

    def _stream_get(self, path: str, params: dict) -> io.BytesIO:
        url = f'{self._base_url()}{path}'
        resp = requests.get(
            url,
            headers=self._auth_headers(),
            params=params,
            stream=True,
            timeout=(10, 300),
        )
        resp.raise_for_status()
        return _drain(resp)

    def _stream_post(self, path: str, params: dict, data: bytes, content_type: str) -> io.BytesIO:
        url = f'{self._base_url()}{path}'
        resp = requests.post(
            url,
            headers={**self._auth_headers(), 'Content-Type': content_type},
            params=params,
            data=data,
            stream=True,
            timeout=(10, 300),
        )
        resp.raise_for_status()
        return _drain(resp)

    def fetch_country(
        self,
        country_code: str,
        *,
        format: Literal['csv', 'parquet'] = 'csv',
        as_of: Optional[str] = None,
        filters: Optional[dict] = None,
    ) -> io.BytesIO:
        params: dict = {'format': format}
        if as_of:
            params['as_of'] = as_of
        _apply_filters(params, filters)
        return self._stream_get(f'/v1/exposure/country/{country_code}', params)

    def fetch_bbox(
        self,
        bbox: list,
        *,
        format: Literal['csv', 'parquet'] = 'csv',
        as_of: Optional[str] = None,
        filters: Optional[dict] = None,
    ) -> io.BytesIO:
        params: dict = {
            'bbox': ','.join(str(c) for c in bbox),
            'format': format,
        }
        if as_of:
            params['as_of'] = as_of
        _apply_filters(params, filters)
        return self._stream_get('/v1/exposure/bbox', params)

    def lookup(
        self,
        locations_stream: io.IOBase,
        fields: list,
        *,
        input_format: Literal['csv', 'parquet'] = 'csv',
        output_format: Literal['csv', 'parquet'] = 'csv',
        match_radius_m: Optional[float] = None,
    ) -> io.BytesIO:
        params: dict = {'format': output_format}
        if fields:
            params['fields'] = ','.join(fields)
        if match_radius_m is not None:
            params['match_radius_m'] = match_radius_m
        content_type = 'application/octet-stream' if input_format == 'parquet' else 'text/csv'
        return self._stream_post(
            '/v1/exposure/lookup',
            params,
            locations_stream.read(),
            content_type,
        )


def _drain(resp) -> io.BytesIO:
    buf = io.BytesIO()
    for chunk in resp.iter_content(chunk_size=65536):
        buf.write(chunk)
    buf.seek(0)
    return buf


def _apply_filters(params: dict, filters: Optional[dict]) -> None:
    if not filters:
        return
    for k, v in filters.items():
        if isinstance(v, list):
            params[k] = ','.join(str(i) for i in v)
        elif v is not None:
            params[k] = v
