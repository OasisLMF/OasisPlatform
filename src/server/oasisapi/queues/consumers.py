from typing import List, TYPE_CHECKING, NamedTuple

from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from django.utils.timezone import now
from rest_framework.serializers import DateTimeField

if TYPE_CHECKING:
    from src.server.oasisapi.analyses.models import Analysis, AnalysisTaskStatus
    from src.server.oasisapi.queues.utils import QueueInfo


class TaskStatusMessageAnalysisItem(NamedTuple):
    analysis: 'Analysis'
    updated_tasks: List['AnalysisTaskStatus']


class TaskStatusMessageItem(NamedTuple):
    queue: 'QueueInfo'
    analyses: List['TaskStatusMessageAnalysisItem']


def build_task_status_message(items: List[TaskStatusMessageItem]):
    from src.server.oasisapi.analyses.serializers import AnalysisSerializer, AnalysisTaskStatusSerializer
    from src.server.oasisapi.queues.serializers import QueueSerializer

    content = {
        'time': DateTimeField().to_representation(now()),
        'type': 'queue_status.updated',
        'content': [
            {
                'queue': QueueSerializer(instance=item.queue).data,
                'analyses': [
                    {
                        'analysis': AnalysisSerializer(instance=analysis.analysis).data,
                        'updated_tasks': AnalysisTaskStatusSerializer(instance=analysis.updated_tasks, many=True).data,
                    }
                    for analysis in item.analyses
                ],
            } for item in items
        ]
    }

    return content


def send_task_status_message(items: List[TaskStatusMessageItem]):
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(
        'queue_status',
        build_task_status_message(items)
    )


class QueueStatusConsumer(AsyncJsonWebsocketConsumer):
    groups = ['queue_status']

    async def queue_status_updated(self, event):
        await self.send_json(event)
