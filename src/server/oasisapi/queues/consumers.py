from enum import Enum
from typing import List, TYPE_CHECKING, NamedTuple

from asgiref.sync import async_to_sync, sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from django.utils.timezone import now
from rest_framework.serializers import DateTimeField

if TYPE_CHECKING:
    from src.server.oasisapi.analyses.models import Analysis, AnalysisTaskStatus
    from src.server.oasisapi.queues.utils import QueueInfo


class ContentStatus(Enum):
    ERROR = 'ERROR'
    SUCCESS = 'SUCCESS'


class TaskStatusMessageAnalysisItem(NamedTuple):
    analysis: 'Analysis'
    updated_tasks: List['AnalysisTaskStatus']


class TaskStatusMessageItem(NamedTuple):
    queue: 'QueueInfo'
    analyses: List['TaskStatusMessageAnalysisItem']


def wrap_message_content(message_type, content, status=ContentStatus.SUCCESS):
    return {
        'time': DateTimeField().to_representation(now()),
        'type': message_type,
        'status': status.name,
        'content': content,
    }


def build_task_status_message(items: List[TaskStatusMessageItem], message_type='queue_status.updated'):
    from src.server.oasisapi.analyses.serializers import AnalysisSerializer, AnalysisTaskStatusSerializer
    from src.server.oasisapi.queues.serializers import QueueSerializer

    return wrap_message_content(
        message_type,
        [
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
        ],
    )


def send_task_status_message(items: dict):
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(
        'queue_status',
        items
    )


def build_all_queue_status_message(analysis_filter=None, message_type='queue_status.updated'):
    from src.server.oasisapi.analyses.models import Analysis
    from src.server.oasisapi.queues.utils import filter_queues_info

    if analysis_filter:
        analyses = Analysis.objects.filter(**analysis_filter)
        queue_names = analyses.values_list('sub_task_statuses__queue_name', flat=True).distinct()
    else:
        analyses = Analysis.objects.filter(status__in=[Analysis.status_choices.INPUTS_GENERATION_STARTED, Analysis.status_choices.RUN_STARTED])
        queue_names = None

    # filter queues with some nodes or activity
    all_queues = filter_queues_info(queue_names)
    active_queues = list(q for q in all_queues if (q['worker_count'] or q['pending_count'] or q['running_count'] or q['queued_count']))

    status_message = []
    for q in active_queues:
        status_message.append(TaskStatusMessageItem(
            queue=q,
            analyses=[TaskStatusMessageAnalysisItem(
                analysis=a,
                updated_tasks=[]
            ) for a in analyses.filter(**{
                'sub_task_statuses__queue_name': q['name'],
            }).distinct()]
        ))

    return build_task_status_message(status_message, message_type=message_type)


class QueueStatusConsumer(AsyncJsonWebsocketConsumer):
    groups = ['queue_status']

    async def connect(self):
        if self.scope['user'].is_authenticated:
            await super().connect()
            await self.send_json(await sync_to_async(build_all_queue_status_message, thread_sensitive=True)())

    async def receive_json(self, content, **kwargs):
        if not isinstance(content, dict):
            await self.send_json(wrap_message_content(
                None,
                {'detail': 'Payload should be a dictionary.'},
                status=ContentStatus.ERROR,
            ))
            return

        process_type = content.get('type')
        processor = {
            'queue_status.filter': self._process_queue_status_filter,
        }.get(process_type)

        if processor:
            # if we have found a processor for the type use it
            data = content.get('content')
            if not data:
                await self.send_json(wrap_message_content(
                    process_type,
                    {'detail': 'Payload "content" was not set.'},
                    status=ContentStatus.ERROR,
                ))
                return

            await processor(data)
        else:
            # if we didnt find a processor raise an error
            await self.send_json(wrap_message_content(
                None,
                {'detail': f'type "{process_type}" is not valid.'},
                status=ContentStatus.ERROR,
            ))

    async def _process_queue_status_filter(self, filters):
        #
        # TODO: add better cleaning here, we could use django filters or something similar
        #
        if not isinstance(filters, dict):
            await self.send_json(wrap_message_content(
                None,
                {'detail': 'queue_status.filter "content" should be a dictionary.'},
                status=ContentStatus.ERROR,
            ))
            return

        analysis_filter = {}
        if 'analyses' in filters:
            analysis_filter['id__in'] = filters['analyses']

        await self.send_json(
            await sync_to_async(build_all_queue_status_message, thread_sensitive=True)(analysis_filter, message_type='queue_status.filter')
        )

    async def queue_status_updated(self, event):
        await self.send_json(event)
