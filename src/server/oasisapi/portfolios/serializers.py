from rest_framework import serializers

from django.contrib.sites.shortcuts import get_current_site

from .models import Portfolio


class PortfolioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portfolio
        fields = (
            'name',
            'id',
            'created',
            'modified',
            'accounts_file',
            'location_file',
            'reinsurance_info_file',
            'reinsurance_source_file',
        )

    def create(self, validated_data):
        data = dict(validated_data)
        if not data.get('creator') and 'request' in self.context:
            data['creator'] = self.context.get('request').user
        return super(PortfolioSerializer, self).create(data)

    def to_representation(self, instance):
        result = super(PortfolioSerializer, self).to_representation(instance)
        domain = get_current_site(self.context.get('request')).domain
        result.update({'create_analysis': 'http://{}{}'.format(domain, instance.get_absolute_create_analysis_url())})
        return result
