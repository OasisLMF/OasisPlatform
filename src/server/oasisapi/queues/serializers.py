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


class WebsocketAnalysesSerializer(serializers.Serializer):
    analysis = serializers.SerializerMethodField()
    updated_tasks = serializers.SerializerMethodField()

    @swagger_serializer_method(serializer_or_field=AnalysisSerializer())
    def get_analysis(self, instance, *args, **kwargs):
        pass
        #return AnalysisSerializer(instance.profiles, many=True).data

    @swagger_serializer_method(serializer_or_field=AnalysisTaskStatusSerializer(many=True))
    def get_updated_tasks(self, instance, *args, **kwargs):
        pass


class WebsocketContentSerializer(serializers.Serializer):
    queue = serializers.SerializerMethodField()
    analyses = serializers.SerializerMethodField()

    @swagger_serializer_method(serializer_or_field=QueueSerializer)
    def get_queue(self, instance, *args, **kwargs):
        pass

    @swagger_serializer_method(serializer_or_field=WebsocketAnalysesSerializer(many=True))
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

    @swagger_serializer_method(serializer_or_field=WebsocketContentSerializer)
    def get_content(self, instance, *args, **kwargs):
        pass
