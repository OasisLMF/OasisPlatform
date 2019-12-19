from drf_yasg.utils import swagger_serializer_method
from django.core.files import File
from rest_framework import serializers

from .models import AnalysisModel

class AnalysisModelSerializer(serializers.ModelSerializer):
    resource_file = serializers.SerializerMethodField()
    settings = serializers.SerializerMethodField()
    versions = serializers.SerializerMethodField()

    class Meta:
        model = AnalysisModel
        fields = (
            'id',
            'supplier_id',
            'model_id',
            'version_id',
            'created',
            'modified',
            'data_files',
            'resource_file',
            'settings',
            'versions',
        )

    def create(self, validated_data):
        data = validated_data.copy()
        if 'request' in self.context:
            data['creator'] = self.context.get('request').user
        return super(AnalysisModelSerializer, self).create(data)

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_resource_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_resources_file_url(request=request)

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_settings(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_settings_url(request=request)

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_versions(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_versions_url(request=request)


class ModelVersionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisModel
        fields = (
            'ver_ktools',
            'ver_oasislmf',
            'ver_platform',
        )
