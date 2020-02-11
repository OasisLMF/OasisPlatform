from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from src.server.oasisapi.analysis_models.models import AnalysisModel
from src.server.oasisapi.analysis_models.serializers import AnalysisModelSerializer


class QueueSerializer(serializers.Serializer):
    name = serializers.CharField()
    worker_count = serializers.IntegerField()
    queued_count = serializers.IntegerField()
    running_count = serializers.IntegerField()
    models = serializers.SerializerMethodField()

    @swagger_serializer_method(serializer_or_field=AnalysisModelSerializer)
    def get_models(self, instance, *args, **kwargs):
        models = AnalysisModel.objects.filter(queue_associations__queue_name=instance['name']).distinct()
        return AnalysisModelSerializer(instance=models, many=True).data
