from django.contrib.auth.models import Group
from drf_yasg.utils import swagger_serializer_method
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import AnalysisModel, SettingsTemplate
from ..analyses.models import Analysis

from .models import AnalysisModel, ModelScalingOptions, ModelChunkingOptions
from ..permissions.group_auth import validate_and_update_groups, validate_data_files


class AnalysisModelSerializer(serializers.ModelSerializer):
    resource_file = serializers.SerializerMethodField()
    settings = serializers.SerializerMethodField()
    versions = serializers.SerializerMethodField()
    scaling_configuration = serializers.SerializerMethodField()
    chunking_configuration = serializers.SerializerMethodField()
    groups = serializers.SlugRelatedField(many=True, read_only=False, slug_field='name', required=False, queryset=Group.objects.all())

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
            'groups',
        )

    def validate(self, attrs):

        user = self.context.get('request').user

        # Validate and update groups parameter
        validate_and_update_groups(self.partial, user, attrs)
        validate_data_files(user, attrs.get('data_files'))

        return attrs

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


class TemplateSerializer(serializers.ModelSerializer):
    """ Catch-all Analysis settings Template Serializer,
        intended to be called from a nested ViewSet
    """
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = SettingsTemplate
        fields = (
            'id',
            'name',
            'description',
            'file_url',
        )

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_file_url(self, instance):
        request = self.context.get('request')
        model_pk = request.parser_context.get('kwargs', {}).get('models_pk')

        if model_pk and instance.file:
            return instance.get_absolute_settings_template_url(model_pk, request=request)
        else:
            return None


class CreateTemplateSerializer(serializers.ModelSerializer):
    """ Used for creating a new template with an option to copy an existing
        analysis_settings.json file from an analyses via the 'analysis_id' param.
    """
    analysis_id = serializers.IntegerField(required=False)

    class Meta:
        model = SettingsTemplate
        fields = (
            'id',
            'name',
            'description',
            'analysis_id',
        )

    def validate(self, attrs):
        analysis_id = attrs.pop('analysis_id', None)
        if analysis_id:
            try:
                analysis = Analysis.objects.get(id=analysis_id)
            except ObjectDoesNotExist:
                raise ValidationError({"Detail": f"analysis_id = {analysis_id} not found"})
            if not analysis.settings_file:
                raise ValidationError({"Detail": f"analysis_id = {analysis_id} has no attached settings file"})

            new_settings = analysis.copy_file(analysis.settings_file)
            new_settings.name = attrs.get('name')
            new_settings.save()
            attrs['file'] = new_settings

        return super(CreateTemplateSerializer, self).validate(attrs)

    def create(self, validated_data):
        data = dict(validated_data)
        if not data.get('creator') and 'request' in self.context:
            data['creator'] = self.context.get('request').user
        return super(CreateTemplateSerializer, self).create(data)


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
            'dynamic_chunks_max',
            'fixed_analysis_chunks',
            'fixed_lookup_chunks',
        )

    def validate(self, attrs):
        non_neg_fields = [
            'dynamic_locations_per_lookup',
            'dynamic_events_per_analysis',
            'dynamic_chunks_max',
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
                elif value < 1:
                    errors[k] = "Value is less than one."
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
