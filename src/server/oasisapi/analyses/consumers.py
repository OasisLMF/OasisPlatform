from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from django.utils.timezone import now
from rest_framework.serializers import DateTimeField


def build_task_status_message(analysis, tasks, queues):
    from src.server.oasisapi.analyses.serializers import AnalysisSerializer, AnalysisTaskStatusSerializer

    return {
        'time': DateTimeField().to_representation(now()),
        'type': 'analysis_task_status.updated',
        'content': {
            'analysis': AnalysisSerializer(instance=analysis, include_task_statuses=False).to_representation(analysis),
            'tasks': AnalysisTaskStatusSerializer(many=True, instance=tasks).to_representation(tasks),
            'queues': [],
        }
    }


def send_task_status_message(analysis, tasks, queues):
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(
        'analysis_task_status',
        build_task_status_message(analysis, tasks, queues)
    )


class TaskStatusConsumer(AsyncJsonWebsocketConsumer):
    groups = ['analysis_task_status']

    async def analysis_task_status_updated(self, event):
        await self.send_json(event)
