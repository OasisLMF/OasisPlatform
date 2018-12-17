from rest_framework import serializers

from django.contrib.sites.shortcuts import get_current_site

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

        return attrs

    def to_representation(self, instance):
        rep = super(AnalysisSerializer, self).to_representation(instance)

        request = self.context.get('request')
        rep['input_file'] = instance.get_absolute_input_file_url(request=request) if instance.input_file else None
        rep['settings_file'] = instance.get_absolute_settings_file_url(request=request) if instance.settings_file else None
        rep['input_errors_file'] = instance.get_absolute_input_errors_file_url(request=request) if instance.input_errors_file else None
        rep['input_generation_traceback_file'] = instance.get_absolute_input_generation_traceback_file_url(request=request) if instance.input_generation_traceback_file else None
        rep['output_file'] = instance.get_absolute_output_file_url(request=request) if instance.output_file else None
        rep['run_traceback_file'] = instance.get_absolute_run_traceback_file_url(request=request) if instance.run_traceback_file else None

       # if instance.input_file:
       #     rep['input_file'] = {
       #         "uri": instance.get_absolute_input_file_url(request=request), 
       #         "name": instance.input_file.filename,
       #         "stored": str(instance.input_file.file)
       #     }
       # if instance.settings_file:
       #     rep['settings_file'] = {
       #         "uri": instance.get_absolute_settings_file_url(request=request), 
       #         "name": instance.settings_file.filename,
       #         "stored": str(instance.settings_file.file)
       #     }
       # if instance.input_errors_file:
       #     rep['input_errors_file'] = {
       #         "uri": instance.get_absolute_input_errors_file_url(request=request), 
       #         "name": instance.input_errors_file.filename,
       #         "stored": str(instance.input_errors_file.file)
       #     }
       # if instance.input_generation_traceback_file:
       #     rep['input_generation_traceback_file'] = {
       #         "uri": instance.get_absolute_input_generation_traceback_file_url(request=request), 
       #         "name": instance.input_generation_traceback_file.filename,
       #         "stored": str(instance.input_generation_traceback_file.file)
       #     }
       # if instance.output_file:
       #     rep['output_file'] = {
       #         "uri": instance.get_absolute_output_file_url(request=request), 
       #         "name": instance.output_file.filename,
       #         "stored": str(instance.output_file.file)
       #     }
       # if instance.run_traceback_file:
       #     rep['run_traceback_file'] = {
       #         "uri": instance.get_absolute_run_traceback_file_url(request=request), 
       #         "name": instance.run_traceback_file.filename,
       #         "stored": str(instance.run_traceback_file.file)
       #     }
        return rep


class AnalysisCopySerializer(AnalysisSerializer):
    def __init__(self, *args, **kwargs):
        super(AnalysisCopySerializer, self).__init__(*args, **kwargs)

        self.fields['portfolio'].required = False
        self.fields['model'].required = False
        self.fields['name'].required = False
