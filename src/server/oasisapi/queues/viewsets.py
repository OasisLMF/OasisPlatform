from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.response import Response

from .serializers import QueueSerializer, WebsocketSerializer
from .utils import get_queues_info

from .consumers import build_all_queue_status_message

class QueueViewSet(viewsets.ViewSet):
    @swagger_auto_schema(responses={200: QueueSerializer(many=True, read_only=True)})
    def list(self, request, *args, **kwargs):
        """
        Gets the current state of all the registered celery queues
        """
        serializer = QueueSerializer(get_queues_info(), many=True)
        return Response(serializer.data)

class WebsocketViewSet(viewsets.ViewSet):
    @swagger_auto_schema(responses={200: WebsocketSerializer(many=True, read_only=True)})
    def list(self, request, *args, **kwargs):
        """
        This endpoint documents the schema for the WebSocket used for async status updates at
        `ws://<SERVER_IP>:<SERVER_PORT>/ws/v1/queue-status/`

        Issuing a GET call returns the current state returned from the WebSocket.
        To print the websocket directly use the following:
        ```
        pip install websocket_client
        ./manage.py ws_echo --url ws://localhost:8000/ws/v1/queue-status/
        ```
        """
        return Response(build_all_queue_status_message())
