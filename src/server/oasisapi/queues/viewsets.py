from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.response import Response

from .serializers import QueueSerializer
from .utils import get_queues_info


class QueueViewSet(viewsets.ViewSet):
    @swagger_auto_schema(responses={200: QueueSerializer(many=True, read_only=True)})
    def list(self, request, *args, **kwargs):
        """
        Gets the current state of all the registered celery queues
        """
        serializer = QueueSerializer(get_queues_info(), many=True)
        return Response(serializer.data)
