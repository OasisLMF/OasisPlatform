from drf_yasg.utils import swagger_serializer_method
from django.core.files import File
from rest_framework import serializers

from .models import AnalysisModel, ModelScalingOptions, ModelChunkingOptions

class AnalysisModelSerializer(serializers.ModelSerializer):
    resource_file = serializers.SerializerMethodField()
    settings = serializers.SerializerMethodField()
    versions = serializers.SerializerMethodField()
    scaling_configuration = serializers.SerializerMethodField()
    chunking_configuration = serializers.SerializerMethodField()

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
            'scaling_configuration',
            'chunking_configuration',
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

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_scaling_configuration(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_scaling_configuration_url(request=request)

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_chunking_configuration(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_chunking_configuration_url(request=request)

class ModelVersionsSerializer(serializers.ModelSerializer):

    class Meta:
        model = AnalysisModel
        fields = (
            'ver_ktools',
            'ver_oasislmf',
            'ver_platform',
        )


class ModelChunkingConfigSerializer(serializers.ModelSerializer):

    class Meta:
        model = ModelChunkingOptions
        fields = (
            'lookup_strategy',
            'loss_strategy',
            'dynamic_locations_per_lookup',
            'dynamic_events_per_analysis',
            'fixed_analysis_chunks',
            'fixed_lookup_chunks',
        )

    def validate(self, attrs):
        non_neg_fields = [
            'dynamic_locations_per_lookup',
            'dynamic_events_per_analysis',
            'fixed_analysis_chunks',
            'fixed_lookup_chunks',
        ]
        errors = dict()
        for k in non_neg_fields:
            value = self.initial_data.get(k)
            if value is not None:
                # Check type is int
                if not isinstance(value, int):
                    errors[k] = "Value is not type int, found {}".format(type(value))
                    continue
                # Check value is greater than 0
                elif value < 0:
                    errors[k] = "Value is less than zero."
                    continue
                # Data is valid
                attrs[k] = value
        if errors:
            raise serializers.ValidationError(errors)
        return super(ModelChunkingConfigSerializer, self).validate(attrs)


class ModelScalingConfigSerializer(serializers.ModelSerializer):

    class Meta:
        model = ModelScalingOptions
        fields = (
            'scaling_strategy',
            'worker_count_fixed',
            'worker_count_max',
            'chunks_per_worker'
        )

    def validate(self, attrs):
        non_neg_fields = [
            'worker_count_fixed',
            'worker_count_max',
            'chunks_per_worker'
        ]
        errors = dict()
        for k in non_neg_fields:
            value = self.initial_data.get(k)
            if value is not None:
                # Check type is int
                if not isinstance(value, int):
                    errors[k] = "Value is not type int, found {}".format(type(value))
                    continue
                # Check value is greater than 0
                elif value < 0:
                    errors[k] = "Value is less than zero."
                    continue
                # Data is valid
                attrs[k] = value
        if errors:
            raise serializers.ValidationError(errors)
        return super(ModelScalingConfigSerializer, self).validate(attrs)
