from typing import List, TYPE_CHECKING, NamedTuple

from asgiref.sync import async_to_sync, sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from django.utils.timezone import now
from rest_framework.serializers import DateTimeField

if TYPE_CHECKING:
    from src.server.oasisapi.analyses.models import Analysis, AnalysisTaskStatus
    from src.server.oasisapi.queues.utils import QueueInfo, get_queues_info


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


def build_all_queue_status_message():
    from src.server.oasisapi.analyses.models import Analysis
    from src.server.oasisapi.queues.utils import get_queues_info

    # filter queues with some nodes or activity
    all_queues = get_queues_info()
    active_queues = list(q for q in all_queues if (q['worker_count'] or q['pending_count'] or q['running_count'] or q['queued_count']))

    status_message = []
    for q in active_queues:
        status_message.append(TaskStatusMessageItem(
            queue=q,
            analyses=[TaskStatusMessageAnalysisItem(
                analysis=a,
                updated_tasks=[]
            ) for a in Analysis.objects.filter(sub_task_statuses__queue_name=q['name']).distinct()]
        ))

    return build_task_status_message(status_message)


class QueueStatusConsumer(AsyncJsonWebsocketConsumer):
    groups = ['queue_status']

    async def connect(self):
        if self.scope['user'].is_authenticated:
            await super().connect()

        await self.send_json(await sync_to_async(build_all_queue_status_message, thread_sensitive=True)())

    async def queue_status_updated(self, event):
        await self.send_json(event)
