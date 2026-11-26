from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import AnalysisStatusSerializer
from .progress import analysis_progress_updates


class AnalysisStatusView(APIView):
    """
    HTTP equivalent of the `ws/analysis-status/` websocket used by workers to report
    run progress. Sits outside the versioned `v1`/`v2` API, alongside `healthcheck/`
    and `server_info/`, since it's a worker-facing status ping rather than a
    user-facing resource. Unauthenticated to match the websocket's current
    behaviour (the consumer accepts any connection, authenticated or not).
    """
    permission_classes = [AllowAny]

    @extend_schema(request=AnalysisStatusSerializer, responses={204: None}, exclude=True)
    def post(self, request, *args, **kwargs):
        """
        Record progress for a running analysis. Safe to call concurrently from
        multiple worker processes for the same `analysis_pk` - the counts
        (`events_complete`, `gul_processes`, `gul_ready`, `outputs_complete`) are applied as atomic
        SQL increments rather than a read/modify/write, so updates from different
        processes can't clobber one another.
        """
        from src.server.oasisapi.analyses.models import Analysis

        serializer = AnalysisStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        update_fields = analysis_progress_updates(data)
        if update_fields:
            Analysis.objects.filter(pk=data['analysis_pk']).update(**update_fields)

        return Response(status=status.HTTP_204_NO_CONTENT)
