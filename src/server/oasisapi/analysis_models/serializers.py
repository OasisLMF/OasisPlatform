from rest_framework import serializers

from .models import AnalysisModel
from ..data_files.serializers import DataFileSerializer

class AnalysisModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisModel
        fields = (
            'id',
            'supplier_id',
            'model_id',
            'version_id',
            'created',
            'modified',
        )

    def create(self, validated_data):
        data = validated_data.copy()
        if 'request' in self.context:
            data['creator'] = self.context.get('request').user
        return super(AnalysisModelSerializer, self).create(data)

    def to_representation(self, instance):
        rep = super(AnalysisModelSerializer, self).to_representation(instance)

        request = self.context.get('request')
        rep['resource_file'] = instance.get_absolute_resources_file_url(request=request)
        return rep
