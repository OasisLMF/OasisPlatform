from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from src.server.oasisapi.analysis_models.models import AnalysisModel
from src.server.oasisapi.analysis_models.serializers import AnalysisModelSerializer
from src.server.oasisapi.analyses.serializers import AnalysisSerializer, AnalysisTaskStatusSerializer


class QueueSerializer(serializers.Serializer):
    name = serializers.CharField()
    pending_count = serializers.IntegerField()
    worker_count = serializers.IntegerField()
    queued_count = serializers.IntegerField()
    running_count = serializers.IntegerField()
    models = serializers.SerializerMethodField()

    @swagger_serializer_method(serializer_or_field=AnalysisModelSerializer)
    def get_models(self, instance, *args, **kwargs):
        models = [m for m in AnalysisModel.objects.all() if str(m) == instance['name']]
        return AnalysisModelSerializer(instance=models, many=True).data

class WebsocketSerializer(serializers.Serializer):
    """ This is a 'dummy' Serializer to document 
    the WebSocket  schema 
    """
    queue = serializers.SerializerMethodField()
    analyses = serializers.SerializerMethodField()
    updated_tasks = serializers.SerializerMethodField()
    time = serializers.DateField()
    type = serializers.CharField()
    status = serializers.CharField()

    @swagger_serializer_method(serializer_or_field=QueueSerializer)
    def get_queue(self, instance, *args, **kwargs):
        pass
    @swagger_serializer_method(serializer_or_field=AnalysisSerializer(many=True))
    def get_analyses(self, instance, *args, **kwargs):
        pass
    @swagger_serializer_method(serializer_or_field=AnalysisTaskStatusSerializer(many=True))
    def get_updated_tasks(self, instance, *args, **kwargs):
        pass
