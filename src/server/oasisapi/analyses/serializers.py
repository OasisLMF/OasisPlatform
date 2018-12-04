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
        )

    def validate(self, attrs):
        if not attrs.get('creator') and 'request' in self.context:
            attrs['creator'] = self.context.get('request').user
#            attrs['creator_name'] = self.context.get('request').user.username

        return attrs

    def to_representation(self, instance):
        rep = super(AnalysisSerializer, self).to_representation(instance)

        request = self.context.get('request')
        rep['input_file'] = instance.get_absolute_input_file_url(request=request)
        rep['settings_file'] = instance.get_absolute_settings_file_url(request=request)
        rep['input_errors_file'] = instance.get_absolute_input_errors_file_url(request=request)
        rep['input_generation_traceback_file'] = instance.get_absolute_input_generation_traceback_file_url(request=request)
        rep['output_file'] = instance.get_absolute_output_file_url(request=request)
        rep['run_traceback_file'] = instance.get_absolute_run_traceback_file_url(request=request)

        return rep


class AnalysisCopySerializer(AnalysisSerializer):
    def __init__(self, *args, **kwargs):
        super(AnalysisCopySerializer, self).__init__(*args, **kwargs)

        self.fields['portfolio'].required = False
        self.fields['model'].required = False
        self.fields['name'].required = False
