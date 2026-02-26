from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from src.server.oasisapi.analysis_models.models import AnalysisModel
from src.server.oasisapi.analysis_models.v2_api.serializers import AnalysisModelListSerializer
from src.server.oasisapi.analyses.v2_api.serializers import AnalysisSerializerWebSocket, AnalysisTaskStatusSerializer


class QueueSerializer(serializers.Serializer):
    name = serializers.CharField()
    pending_count = serializers.IntegerField()
    queued_count = serializers.IntegerField()
    running_count = serializers.IntegerField()
    queue_message_count = serializers.IntegerField()
    worker_count = serializers.IntegerField()
    models = serializers.SerializerMethodField()

    @extend_schema_field(AnalysisModelListSerializer(many=True))
    def get_models(self, instance, *args, **kwargs):
        queue_name = instance['name'].removesuffix('-v2')
        models = [m for m in AnalysisModel.objects.all() if str(m) == queue_name]
        return AnalysisModelListSerializer(instance=models, many=True).data


class WebsocketAnalysesSerializer(serializers.Serializer):
    analysis = serializers.SerializerMethodField()
    updated_tasks = serializers.SerializerMethodField()

    @extend_schema_field(AnalysisSerializerWebSocket())
    def get_analysis(self, instance, *args, **kwargs):
        pass

    @extend_schema_field(AnalysisTaskStatusSerializer(many=True))
    def get_updated_tasks(self, instance, *args, **kwargs):
        pass


class WebsocketContentSerializer(serializers.Serializer):
    queue = serializers.SerializerMethodField()
    analyses = serializers.SerializerMethodField()

    @extend_schema_field(QueueSerializer)
    def get_queue(self, instance, *args, **kwargs):
        pass

    @extend_schema_field(WebsocketAnalysesSerializer(many=True))
    def get_analyses(self, instance, *args, **kwargs):
        pass


class WebsocketSerializer(serializers.Serializer):
    """ This is a 'dummy' Serializer to document
    the WebSocket  schema
    """
    time = serializers.DateField()
    type = serializers.CharField()
    status = serializers.CharField()
    content = serializers.SerializerMethodField()

    @extend_schema_field(WebsocketContentSerializer(many=True))
    def get_content(self, instance, *args, **kwargs):
        pass
