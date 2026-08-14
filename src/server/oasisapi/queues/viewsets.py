from django.db.models import F
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers import AnalysisStatusSerializer, QueueSerializer, WebsocketSerializer
from .utils import get_queues_info

from .consumers import build_all_queue_status_message


class QueueViewSet(viewsets.ViewSet):
    @extend_schema(responses={200: QueueSerializer(many=True, read_only=True)})
    def list(self, request, *args, **kwargs):
        """
        Gets the current state of all the registered celery queues
        """
        serializer = QueueSerializer(get_queues_info(), many=True)
        return Response(serializer.data)


class WebsocketViewSet(viewsets.ViewSet):
    @extend_schema(responses={200: WebsocketSerializer(many=False, read_only=True)})
    def list(self, request, *args, **kwargs):
        """
        This endpoint documents the schema for the WebSocket used for async status updates at
        `ws://<SERVER_IP>:<SERVER_PORT>/ws/v2/queue-status/`

        Issuing a GET call returns the current state returned from the WebSocket.
        To print the websocket directly use the following:
        ```
        pip install websocket_client
        ./manage.py ws_echo --url ws://localhost:8001/ws/v2/queue-status/
        ```
        """
        return Response(build_all_queue_status_message())


class AnalysisStatusViewSet(viewsets.ViewSet):
    """
    HTTP equivalent of the `ws/analysis-status/` websocket used by workers to report
    run progress. Unauthenticated to match the websocket's current behaviour (the
    consumer accepts any connection, authenticated or not).
    """
    permission_classes = [AllowAny]

    @extend_schema(request=AnalysisStatusSerializer, responses={204: None})
    def create(self, request, *args, **kwargs):
        """
        Record progress for a running analysis. Safe to call concurrently from
        multiple worker processes for the same `analysis_pk` - `events_complete`
        is applied as an atomic SQL increment rather than a read/modify/write, so
        updates from different processes can't clobber one another.
        """
        from src.server.oasisapi.analyses.models import Analysis

        serializer = AnalysisStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        update_fields = {}
        if 'events_total' in data:
            update_fields['num_events_total'] = data['events_total']
            update_fields['num_events_complete'] = 0
        if 'events_complete' in data:
            update_fields['num_events_complete'] = F('num_events_complete') + data['events_complete']

        if update_fields:
            Analysis.objects.filter(pk=data['analysis_pk']).update(**update_fields)

        return Response(status=status.HTTP_204_NO_CONTENT)
