from drf_yasg.utils import swagger_serializer_method
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..models import AnalysisModel, SettingsTemplate
from ...analyses.models import Analysis


class AnalysisModelSerializer(serializers.ModelSerializer):
    settings = serializers.SerializerMethodField()
    versions = serializers.SerializerMethodField()
    ns = 'v1-models'

    class Meta:
        ref_name = "v1_" + __qualname__.split('.')[0]
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
            'run_mode',
        )

    def create(self, validated_data):
        data = validated_data.copy()
        if 'request' in self.context:
            data['creator'] = self.context.get('request').user
        return super(AnalysisModelSerializer, self).create(data)

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_settings(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_settings_url(request=request, namespace=self.ns)

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_versions(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_versions_url(request=request, namespace=self.ns)


class TemplateSerializer(serializers.ModelSerializer):
    """ Catch-all Analysis settings Template Serializer,
        intended to be called from a nested ViewSet
    """
    file_url = serializers.SerializerMethodField()

    class Meta:
        ref_name = "v1_" + __qualname__.split('.')[0]
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
        ref_name = "v1_" + __qualname__.split('.')[0]
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
        ref_name = "v1_" + __qualname__.split('.')[0]
        model = AnalysisModel
        fields = (
            'ver_ktools',
            'ver_oasislmf',
            'ver_platform',
        )
