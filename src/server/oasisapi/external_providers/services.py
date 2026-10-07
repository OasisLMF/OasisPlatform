import io
import json
import logging
from typing import Optional, Tuple

import pandas as pd
from django.core.files import File
from django.utils import timezone

from src.server.oasisapi.files.models import RelatedFile
from .adapters import get_adapter
from .models import ExternalJob

logger = logging.getLogger(__name__)


def get_provider_settings(provider: str):
    """
    Return an ExternalProviderSettings instance or a settings proxy sourced
    from Django settings (for development without a DB row).
    """
    from .models import ExternalProviderSettings
    try:
        return ExternalProviderSettings.objects.get(provider=provider)
    except ExternalProviderSettings.DoesNotExist:
        pass

    from django.conf import settings as django_settings
    base_url = getattr(django_settings, 'GXM_BASE_URL', '')
    if provider == 'gxm' and base_url:
        class _SettingsProxy:
            pass
        s = _SettingsProxy()
        s.base_url = base_url
        s.client_id = getattr(django_settings, 'GXM_CLIENT_ID', '')
        s.client_secret = getattr(django_settings, 'GXM_CLIENT_SECRET', '')
        s.default_as_of = None
        return s

    raise ValueError(f'No settings found for provider {provider!r}; create an ExternalProviderSettings record or set GXM_BASE_URL')


def run_location_file(job_id: str, initiator_id: int) -> None:
    from django.contrib.auth import get_user_model
    User = get_user_model()

    job = ExternalJob.objects.select_related('portfolio').get(id=job_id)
    initiator = User.objects.get(pk=initiator_id)
    _mark_running(job)

    try:
        provider_settings = get_provider_settings(job.provider)
        adapter = get_adapter(job.provider, provider_settings)

        req = job.request_data
        fmt = req.get('format', 'csv')
        filters = dict(req.get('filters') or {})
        bbox = filters.pop('bbox', None)

        if bbox:
            buf = adapter.fetch_bbox(
                bbox,
                format=fmt,
                as_of=req.get('as_of'),
                filters=filters or None,
            )
        else:
            buf = adapter.fetch_country(
                req['country_code'],
                format=fmt,
                as_of=req.get('as_of'),
                filters=filters or None,
            )

        filename = f'locations_{job.portfolio_id}_{job.provider}{_ext(fmt)}'
        result_file = _persist_file(buf, filename, _content_type(fmt), initiator)

        portfolio = job.portfolio
        _replace_location_file(portfolio, result_file, source='external', provider=job.provider, audit=None)

        job.result_file = result_file
        _mark_completed(job)

    except Exception as exc:
        logger.exception('External location-file job %s failed', job_id)
        _mark_failed(job, exc)
        raise


def run_enrich(job_id: str, initiator_id: int) -> None:
    from django.contrib.auth import get_user_model
    User = get_user_model()

    job = ExternalJob.objects.select_related('portfolio').get(id=job_id)
    initiator = User.objects.get(pk=initiator_id)
    _mark_running(job)

    try:
        portfolio = job.portfolio
        if not portfolio.location_file:
            raise ValueError('Portfolio has no location file to enrich')

        provider_settings = get_provider_settings(job.provider)
        adapter = get_adapter(job.provider, provider_settings)

        req = job.request_data
        fmt = req.get('format', 'csv')
        fields = req.get('fields', [])
        match_radius_m = req.get('match_radius_m')
        overwrite = req.get('overwrite', False)

        portfolio.location_file.file.seek(0)
        original_content_type = portfolio.location_file.content_type
        original_format = 'parquet' if original_content_type == 'application/octet-stream' else 'csv'
        original_bytes = portfolio.location_file.file.read()

        enriched_buf = adapter.lookup(
            io.BytesIO(original_bytes),
            fields,
            input_format=original_format,
            output_format=fmt,
            match_radius_m=match_radius_m,
        )

        audit_data: Optional[dict] = None
        if not overwrite:
            enriched_buf, audit_data = _merge_non_destructive(
                io.BytesIO(original_bytes),
                enriched_buf,
                fields,
                original_format,
                fmt,
            )

        filename = f'locations_{portfolio.pk}_{job.provider}_enriched{_ext(fmt)}'
        result_file = _persist_file(enriched_buf, filename, _content_type(fmt), initiator)

        audit_file: Optional[RelatedFile] = None
        if audit_data is not None:
            audit_buf = io.BytesIO(json.dumps(audit_data, default=str).encode())
            audit_file = _persist_file(
                audit_buf,
                f'enrichment_audit_{job.id}.json',
                'application/json',
                initiator,
            )

        _replace_location_file(portfolio, result_file, source='merged', provider=job.provider, audit=audit_file)

        job.result_file = result_file
        job.audit_file = audit_file
        _mark_completed(job)

    except Exception as exc:
        logger.exception('External enrichment job %s failed', job_id)
        _mark_failed(job, exc)
        raise


def _merge_non_destructive(
    original_buf: io.BytesIO,
    enriched_buf: io.BytesIO,
    fields: list,
    original_format: str,
    output_format: str,
) -> Tuple[io.BytesIO, dict]:
    """
    Merge enriched values into original rows only where the original value is blank/null.
    Returns (merged_buf, audit_dict).
    """
    orig_df = _read_df(original_buf, original_format)
    enr_df = _read_df(enriched_buf, output_format)

    audit: dict = {}
    for field in fields:
        if field not in enr_df.columns:
            continue
        if field not in orig_df.columns:
            orig_df[field] = None

        filled_indices = []
        for idx in orig_df.index:
            if idx >= len(enr_df):
                break
            orig_val = orig_df.at[idx, field]
            if _is_blank(orig_val):
                new_val = enr_df.at[idx, field]
                if not _is_blank(new_val):
                    orig_df.at[idx, field] = new_val
                    filled_indices.append(int(idx))

        if filled_indices:
            audit[field] = {'filled_row_indices': filled_indices, 'provider': 'gxm'}

    return _write_df(orig_df, output_format), audit


def _is_blank(val) -> bool:
    if val is None:
        return True
    if val != val:  # NaN
        return True
    return str(val).strip() == ''


def _content_type(format: str) -> str:
    return 'application/octet-stream' if format == 'parquet' else 'text/csv'


def _ext(format: str) -> str:
    return '.parquet' if format == 'parquet' else '.csv'


def _read_df(buf: io.BytesIO, format: str) -> pd.DataFrame:
    buf.seek(0)
    return pd.read_parquet(buf) if format == 'parquet' else pd.read_csv(buf)


def _write_df(df: pd.DataFrame, format: str) -> io.BytesIO:
    buf = io.BytesIO()
    if format == 'parquet':
        df.to_parquet(buf, index=False)
    else:
        df.to_csv(buf, index=False)
    buf.seek(0)
    return buf


def _persist_file(buf: io.BytesIO, filename: str, content_type: str, user) -> RelatedFile:
    return RelatedFile.objects.create(
        file=File(buf, name=filename),
        filename=filename,
        content_type=content_type,
        creator=user,
    )


def _replace_location_file(portfolio, new_file: RelatedFile, source: str, provider: str, audit) -> None:
    old_file = portfolio.location_file
    portfolio.location_file = new_file
    portfolio.location_file_source = source
    portfolio.location_file_external_provider = provider
    portfolio.location_file_audit = audit
    portfolio.save(update_fields=[
        'location_file',
        'location_file_source',
        'location_file_external_provider',
        'location_file_audit',
    ])
    if old_file:
        old_file.delete()


def _mark_running(job: ExternalJob) -> None:
    job.status = ExternalJob.Status.RUNNING
    job.started = timezone.now()
    job.save(update_fields=['status', 'started'])


def _mark_completed(job: ExternalJob) -> None:
    job.status = ExternalJob.Status.COMPLETED
    job.finished = timezone.now()
    save_fields = ['status', 'finished']
    if job.result_file_id:
        save_fields.append('result_file')
    if job.audit_file_id:
        save_fields.append('audit_file')
    job.save(update_fields=save_fields)


def _mark_failed(job: ExternalJob, exc: Exception) -> None:
    job.status = ExternalJob.Status.FAILED
    job.error_message = str(exc)
    job.finished = timezone.now()
    job.save(update_fields=['status', 'error_message', 'finished'])
