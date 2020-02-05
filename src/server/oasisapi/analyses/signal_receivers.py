from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .serializers import AnalysisSerializer, AnalysisTaskStatusSerializer


def task_updated(instance, *args, **kwargs):
    layer = get_channel_layer()
    async_to_sync(layer.group_send)('analysis_task_status', {
        'type': 'analysis_task_status.updated',
        'content': {
            'analysis': AnalysisSerializer(instance=instance.analysis).to_representation(instance.analysis),
            'tasks': AnalysisTaskStatusSerializer(many=True, instance=[instance]).to_representation([instance])
        }
    })
