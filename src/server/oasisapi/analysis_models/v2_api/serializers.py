from django.contrib.auth.models import Group
from drf_yasg.utils import swagger_serializer_method
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..models import AnalysisModel, SettingsTemplate
from ...analyses.models import Analysis

from ..models import AnalysisModel, ModelScalingOptions, ModelChunkingOptions
from ...permissions.group_auth import validate_and_update_groups, validate_data_files

from ...schemas.serializers import ModelParametersSerializer
from django.core.files import File
from tempfile import TemporaryFile
from ...files.models import RelatedFile


def create_settings_file(data, user):
    json_serializer = ModelParametersSerializer()
    with TemporaryFile() as tmp_file:
        tmp_file.write(data.encode('utf-8'))
        tmp_file.seek(0)

        return RelatedFile.objects.create(
            file=File(tmp_file, name=json_serializer.filename),
            filename=json_serializer.filename,
            content_type='application/json',
            creator=user,
        )


class AnalysisModelListSerializer(serializers.Serializer):
    """ Read Only Model Deserializer for efficiently returning a list of all
        entries in DB
    """
    id = serializers.IntegerField(read_only=True)
    supplier_id = serializers.CharField(read_only=True)
    model_id = serializers.CharField(read_only=True)
    version_id = serializers.CharField(read_only=True)
    created = serializers.DateTimeField(read_only=True)
    modified = serializers.DateTimeField(read_only=True)
    settings = serializers.SerializerMethodField()
    versions = serializers.SerializerMethodField()
    scaling_configuration = serializers.SerializerMethodField()
    chunking_configuration = serializers.SerializerMethodField()
    groups = serializers.SlugRelatedField(many=True, read_only=False, slug_field='name', required=False, queryset=Group.objects.all())
    settings = serializers.SerializerMethodField()
    run_mode = serializers.CharField(read_only=True)
    namespace = 'v2-models'

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_settings(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_settings_url(request=request, namespace=self.namespace)

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_versions(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_versions_url(request=request, namespace=self.namespace)

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_scaling_configuration(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_scaling_configuration_url(request=request, namespace=self.namespace)

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_chunking_configuration(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_chunking_configuration_url(request=request, namespace=self.namespace)


class AnalysisModelSerializer(serializers.ModelSerializer):
    settings = serializers.SerializerMethodField()
    versions = serializers.SerializerMethodField()
    scaling_configuration = serializers.SerializerMethodField()
    chunking_configuration = serializers.SerializerMethodField()
    groups = serializers.SlugRelatedField(many=True, read_only=False, slug_field='name', required=False, queryset=Group.objects.all())
    settings = serializers.SerializerMethodField()
    namespace = 'v2-models'

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
            'settings',
            'versions',
            'scaling_configuration',
            'chunking_configuration',
            'groups',
            'run_mode',
        )

    def validate(self, attrs):

        user = self.context.get('request').user

        # Validate and update groups parameter
        validate_and_update_groups(self.partial, user, attrs)
        validate_data_files(user, attrs.get('data_files'))

        if attrs.get('settings'):
            attrs['settings'] = ModelParametersSerializer().validate(attrs.get('settings'))

        return attrs

    def to_internal_value(self, data):
        settings = data.get('settings', {})
        data = super(AnalysisModelSerializer, self).to_internal_value(data)
        data['settings'] = ModelParametersSerializer().to_internal_value(settings)
        return data

    def update(self, instance, validated_data):
        data = validated_data.copy()
        settings = data.pop('settings', {})
        if settings:
            instance.resource_file = create_settings_file(settings, instance.creator)

        return super(AnalysisModelSerializer, self).update(instance, validated_data)

    def create(self, validated_data):
        data = validated_data.copy()
        settings = data.pop('settings', {})
        if 'request' in self.context:
            data['creator'] = self.context.get('request').user

        instance = super(AnalysisModelSerializer, self).create(data)
        if settings:
            instance.resource_file = create_settings_file(settings, data['creator'])

        instance.save()
        return instance

    @swagger_serializer_method(serializer_or_field=ModelParametersSerializer)
    def get_settings(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_settings_url(request=request, namespace=self.namespace)

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_versions(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_versions_url(request=request, namespace=self.namespace)

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_scaling_configuration(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_scaling_configuration_url(request=request, namespace=self.namespace)

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_chunking_configuration(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_chunking_configuration_url(request=request, namespace=self.namespace)


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
            'worker_count_min',
            'chunks_per_worker'
        )

    def validate(self, attrs):
        non_neg_fields = [
            'worker_count_fixed',
            'worker_count_max',
            'worker_count_min',
            'chunks_per_worker'
        ]
        errors = dict()

        # check for negative values
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

        # Check that `worker_count_min` < `worker_count_max`
        m_id = self.context['request'].parser_context['kwargs']['pk']
        try:
            current_val = ModelScalingOptions.objects.get(id=m_id)
        except ModelScalingOptions.DoesNotExist:
            # create a default config object for validation
            current_val = ModelScalingOptions()

        wrk_min = self.initial_data.get('worker_count_min', current_val.worker_count_min)
        wrk_max = self.initial_data.get('worker_count_max', current_val.worker_count_max)
        if 'worker_count_min' in self.initial_data and (wrk_min > wrk_max):
            errors['worker_count_min'] = f"Value '{wrk_min}' must be less than 'worker_count_max: {wrk_max}'"
        if 'worker_count_max' in self.initial_data and (wrk_max < wrk_min):
            errors['worker_count_max'] = f"Value '{wrk_max}' must be greater than 'worker_count_min: {wrk_min}'"

        if errors:
            raise serializers.ValidationError(errors)
        return super(ModelScalingConfigSerializer, self).validate(attrs)
