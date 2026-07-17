import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from src.server.oasisapi.portfolios.models import Portfolio
from src.server.oasisapi.permissions.group_auth import validate_user_is_owner
from .adapters import SUPPORTED_PROVIDERS
from .feature_flag import is_enabled
from .models import ExternalJob, ExternalProviderSettings
from .serializers import (
    ExternalEnrichRequestSerializer,
    ExternalJobAcceptedSerializer,
    ExternalJobSerializer,
    ExternalLocationFileRequestSerializer,
    ExternalProviderSettingsSerializer,
)

logger = logging.getLogger(__name__)


def _require_feature():
    if not is_enabled():
        raise NotFound('External providers feature is not enabled on this deployment')


def _require_provider(provider: str):
    if provider not in SUPPORTED_PROVIDERS:
        raise NotFound(f'Unknown provider: {provider!r}')


def _get_portfolio(portfolio_pk, user) -> Portfolio:
    try:
        portfolio = Portfolio.objects.get(pk=portfolio_pk)
    except Portfolio.DoesNotExist:
        raise NotFound(f'Portfolio {portfolio_pk} not found')
    if not validate_user_is_owner(user, portfolio):
        raise PermissionDenied
    return portfolio


class ExternalLocationFileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ExternalLocationFileRequestSerializer,
        responses={202: ExternalJobAcceptedSerializer},
        summary='Fetch OED location file from an external provider (UC1)',
        description=(
            'Asynchronously fetches a country-level OED location file from the named provider '
            'and attaches it to the portfolio. Returns 202 with a job_id immediately; '
            'poll external_jobs/{job_id}/ to track progress.'
        ),
    )
    def post(self, request, provider, portfolio_pk):
        _require_feature()
        _require_provider(provider)
        portfolio = _get_portfolio(portfolio_pk, request.user)

        serializer = ExternalLocationFileRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        filters = dict(data.get('filters') or {})
        if 'bbox' in filters:
            filters['bbox'] = list(filters['bbox'])

        job = ExternalJob.objects.create(
            provider=provider,
            job_type=ExternalJob.JobType.LOCATION_FILE,
            portfolio=portfolio,
            initiator=request.user,
            request_data={
                'country_code': data['country_code'],
                'format': data.get('format', 'csv'),
                'as_of': data['as_of'].isoformat() if data.get('as_of') else None,
                'filters': filters,
            },
        )

        from .tasks import run_external_location_file_task
        celery_task = run_external_location_file_task.apply_async(
            args=[str(job.id), request.user.pk],
            queue='oasis-internal-worker',
        )
        job.task_id = celery_task.id
        job.save(update_fields=['task_id'])

        accepted = ExternalJobAcceptedSerializer({
            'job_id': job.id,
            'status': job.status,
            'status_url': _job_url(request, provider, portfolio_pk, job.id),
        })
        return Response(accepted.data, status=status.HTTP_202_ACCEPTED)


class ExternalEnrichView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ExternalEnrichRequestSerializer,
        responses={202: ExternalJobAcceptedSerializer},
        summary='Enrich an existing OED location file with provider attributes (UC2)',
        description=(
            'Asynchronously looks up missing OED fields from the named provider '
            'for each row in the portfolio\'s existing location file. '
            'User-supplied values are never overwritten unless overwrite=true. '
            'Returns 202 with a job_id; poll external_jobs/{job_id}/ to track progress.'
        ),
    )
    def post(self, request, provider, portfolio_pk):
        _require_feature()
        _require_provider(provider)
        portfolio = _get_portfolio(portfolio_pk, request.user)

        if not portfolio.location_file:
            return Response(
                {'detail': 'Portfolio has no location file; upload one before enriching.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ExternalEnrichRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        job = ExternalJob.objects.create(
            provider=provider,
            job_type=ExternalJob.JobType.ENRICH,
            portfolio=portfolio,
            initiator=request.user,
            request_data={
                'fields': data['fields'],
                'format': data.get('format', 'csv'),
                'match_radius_m': data.get('match_radius_m'),
                'overwrite': data.get('overwrite', False),
            },
        )

        from .tasks import run_external_enrich_task
        celery_task = run_external_enrich_task.apply_async(
            args=[str(job.id), request.user.pk],
            queue='oasis-internal-worker',
        )
        job.task_id = celery_task.id
        job.save(update_fields=['task_id'])

        accepted = ExternalJobAcceptedSerializer({
            'job_id': job.id,
            'status': job.status,
            'status_url': _job_url(request, provider, portfolio_pk, job.id),
        })
        return Response(accepted.data, status=status.HTTP_202_ACCEPTED)


class ExternalJobDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ExternalJobSerializer

    def get_object(self):
        _require_feature()
        provider = self.kwargs['provider']
        portfolio_pk = self.kwargs['portfolio_pk']
        job_id = self.kwargs['job_id']
        _require_provider(provider)
        portfolio = _get_portfolio(portfolio_pk, self.request.user)
        try:
            return ExternalJob.objects.get(id=job_id, provider=provider, portfolio=portfolio)
        except ExternalJob.DoesNotExist:
            raise NotFound(f'Job {job_id} not found')


class ExternalJobListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ExternalJobSerializer

    def get_queryset(self):
        _require_feature()
        provider = self.kwargs['provider']
        portfolio_pk = self.kwargs['portfolio_pk']
        _require_provider(provider)
        portfolio = _get_portfolio(portfolio_pk, self.request.user)
        return ExternalJob.objects.filter(provider=provider, portfolio=portfolio)


class ExternalProviderSettingsView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(responses={200: ExternalProviderSettingsSerializer})
    def get(self, request, provider):
        _require_provider(provider)
        try:
            obj = ExternalProviderSettings.objects.get(provider=provider)
        except ExternalProviderSettings.DoesNotExist:
            raise NotFound(f'Settings for provider {provider!r} not found')
        return Response(ExternalProviderSettingsSerializer(obj, context={'request': request}).data)

    @extend_schema(
        request=ExternalProviderSettingsSerializer,
        responses={200: ExternalProviderSettingsSerializer},
    )
    def put(self, request, provider):
        _require_provider(provider)
        try:
            obj = ExternalProviderSettings.objects.get(provider=provider)
            serializer = ExternalProviderSettingsSerializer(
                obj, data=request.data, partial=True, context={'request': request}
            )
        except ExternalProviderSettings.DoesNotExist:
            serializer = ExternalProviderSettingsSerializer(
                data=request.data, context={'request': request}
            )
        serializer.is_valid(raise_exception=True)
        serializer.save(provider=provider)
        return Response(serializer.data)


def _job_url(request, provider, portfolio_pk, job_id) -> str:
    from rest_framework.reverse import reverse
    return reverse(
        'v2-external-providers:external-job-detail',
        kwargs={'provider': provider, 'portfolio_pk': portfolio_pk, 'job_id': str(job_id)},
        request=request,
    )
