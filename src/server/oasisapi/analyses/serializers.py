from rest_framework import serializers

from .models import Analysis


class AnalysisSerializer(serializers.ModelSerializer):
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
            'complex_model_data_files'
        )

    def validate(self, attrs):
        if not attrs.get('creator') and 'request' in self.context:
            attrs['creator'] = self.context.get('request').user

        return attrs

    def to_representation(self, instance):
        rep = super(AnalysisSerializer, self).to_representation(instance)

        request = self.context.get('request')
        rep['input_file'] = instance.get_absolute_input_file_url(request=request) if instance.input_file else None
        rep['settings_file'] = instance.get_absolute_settings_file_url(request=request) if instance.settings_file else None
        rep['lookup_errors_file'] = instance.get_absolute_lookup_errors_file_url(request=request) if instance.lookup_errors_file else None
        rep['lookup_success_file'] = instance.get_absolute_lookup_success_file_url(request=request) if instance.lookup_success_file else None
        rep['exposure_validation_file'] = instance.get_absolute_exposure_validation_file_url(request=request) if instance.exposure_validation_file else None
        rep['input_generation_traceback_file'] = instance.get_absolute_input_generation_traceback_file_url(request=request) if instance.input_generation_traceback_file else None
        rep['output_file'] = instance.get_absolute_output_file_url(request=request) if instance.output_file else None
        rep['run_traceback_file'] = instance.get_absolute_run_traceback_file_url(request=request) if instance.run_traceback_file else None
        return rep


class AnalysisCopySerializer(AnalysisSerializer):
    def __init__(self, *args, **kwargs):
        super(AnalysisCopySerializer, self).__init__(*args, **kwargs)

        self.fields['portfolio'].required = False
        self.fields['model'].required = False
        self.fields['name'].required = False
