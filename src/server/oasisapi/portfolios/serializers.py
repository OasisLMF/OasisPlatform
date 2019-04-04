from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..analyses.serializers import AnalysisSerializer
from .models import Portfolio


class PortfolioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portfolio
        fields = (
            'id',
            'name',
            'created',
            'modified',
        )

    def create(self, validated_data):
        data = dict(validated_data)
        if not data.get('creator') and 'request' in self.context:
            data['creator'] = self.context.get('request').user
        return super(PortfolioSerializer, self).create(data)

    def to_representation(self, instance):
        rep = super(PortfolioSerializer, self).to_representation(instance)

        request = self.context.get('request')

        # rep['accounts_file'] = instance.get_absolute_accounts_file_url(request=request) if instance.accounts_file else 'null'
        rep['accounts_file'] = None
        rep['location_file'] = None
        rep['reinsurance_info_file'] = None
        rep['reinsurance_source_file'] = None

        if instance.accounts_file:
            rep['accounts_file'] = {
                "uri": instance.get_absolute_accounts_file_url(request=request),
                "name": instance.accounts_file.filename,
                "stored": str(instance.accounts_file.file)

            }

        if instance.location_file:
            rep['location_file'] = {
                "uri": instance.get_absolute_location_file_url(request=request),
                "name": instance.location_file.filename,
                "stored": str(instance.location_file.file)
            }

        if instance.reinsurance_info_file:
            rep['reinsurance_info_file'] = {
                "uri": instance.get_absolute_reinsurance_info_file_url(request=request),
                "name": instance.reinsurance_info_file.filename,
                "stored": str(instance.reinsurance_info_file.file)
            }

        if instance.reinsurance_source_file:
            rep['reinsurance_source_file'] = {
                "uri": instance.get_absolute_reinsurance_source_file_url(request=request),
                "name": instance.reinsurance_source_file.filename,
                "stored": str(instance.reinsurance_source_file.file)
            }
        return rep


class CreateAnalysisSerializer(AnalysisSerializer):
    class Meta(AnalysisSerializer.Meta):
        fields = ['name', 'model']

    def __init__(self, portfolio=None, *args, **kwargs):
        self.portfolio = portfolio
        super(CreateAnalysisSerializer, self).__init__(*args, **kwargs)

    def validate(self, attrs):
        attrs['portfolio'] = self.portfolio
        if not self.portfolio.location_file:
            raise ValidationError({'portfolio': '"location_file" must not be null'})

        return attrs

    def create(self, validated_data):
        data = dict(validated_data)
        if 'request' in self.context:
            data['creator'] = self.context.get('request').user
        return super(CreateAnalysisSerializer, self).create(data)
