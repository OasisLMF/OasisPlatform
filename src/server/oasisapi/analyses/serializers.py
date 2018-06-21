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
            'settings_file',
            'input_file',
            'input_errors_file',
            'output_file',
            'status',
        )

    def create(self, validated_data):
        data = dict(validated_data)
        if not data.get('creator') and 'request' in self.context:
            data['creator'] = self.context.get('request').user
        return super(AnalysisSerializer, self).create(data)

    def save(self, **kwargs):
        data = dict(kwargs)
        if not data.get('creator') and 'request' in self.context:
            data['creator'] = self.context.get('request').user
        return super(AnalysisSerializer, self).save(**data)

    def to_representation(self, instance):
        result = super(AnalysisSerializer, self).to_representation(instance)
        domain = get_current_site(self.context.get('request')).domain
        result.update({'cancel_analysis': 'http://{}{}'.format(domain, instance.get_absolute_cancel_url())})
        return result
