from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from .models import Analysis
from ..schemas.custom_swagger import load_json_schema

class AnalysisSerializer(serializers.ModelSerializer):
    input_file = serializers.SerializerMethodField()
    settings_file = serializers.SerializerMethodField()
    lookup_errors_file = serializers.SerializerMethodField()
    lookup_success_file = serializers.SerializerMethodField()
    lookup_validation_file = serializers.SerializerMethodField()
    summary_levels_file = serializers.SerializerMethodField()
    input_generation_traceback_file = serializers.SerializerMethodField()
    output_file = serializers.SerializerMethodField()
    run_traceback_file = serializers.SerializerMethodField()

    class Meta:
        model = Analysis
        fields = (
            'created',
            'modified',
            'name',
            'id',
            'portfolio',
            'model',
            'status',
            'task_started',
            'task_finished',
            'complex_model_data_files',
            'input_file',
            'settings_file',
            'lookup_errors_file',
            'lookup_success_file',
            'lookup_validation_file',
            'summary_levels_file',
            'input_generation_traceback_file',
            'output_file',
            'run_traceback_file'
        )

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_input_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_input_file_url(request=request) if instance.input_file else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_settings_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_settings_file_url(request=request) if instance.settings_file else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_lookup_errors_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_lookup_errors_file_url(request=request) if instance.lookup_errors_file else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_lookup_success_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_lookup_success_file_url(request=request) if instance.lookup_success_file else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_lookup_validation_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_lookup_validation_file_url(request=request) if instance.lookup_validation_file else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_summary_levels_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_summary_levels_file_url(request=request) if instance.summary_levels_file else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_input_generation_traceback_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_input_generation_traceback_file_url(request=request) if instance.input_generation_traceback_file else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_output_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_output_file_url(request=request) if instance.output_file else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_run_traceback_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_run_traceback_file_url(request=request) if instance.run_traceback_file else None

    def validate(self, attrs):
        if not attrs.get('creator') and 'request' in self.context:
            attrs['creator'] = self.context.get('request').user
        return attrs


class AnalysisCopySerializer(AnalysisSerializer):
    def __init__(self, *args, **kwargs):
        super(AnalysisCopySerializer, self).__init__(*args, **kwargs)

        self.fields['portfolio'].required = False
        self.fields['model'].required = False
        self.fields['name'].required = False


class AnalysisSettingsJSON(serializers.Serializer):
    # https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html#module-drf_yasg.openapi
    # https://medium.com/@aleemsaadullah/adding-validation-support-for-jsonfield-in-django-2e26779dccc
    class Meta:
        swagger_schema_fields = load_json_schema('analysis_settings.json')
