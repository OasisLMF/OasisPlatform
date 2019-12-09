from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..analyses.serializers import AnalysisSerializer
from .models import Portfolio

from ..schemas.serializers import (
    LocFileSerializer,
    AccFileSerializer,
    ReinsInfoFileSerializer,
    ReinsScopeFileSerializer,
)


class PortfolioSerializer(serializers.ModelSerializer):
    accounts_file = serializers.SerializerMethodField()
    location_file = serializers.SerializerMethodField()
    reinsurance_info_file = serializers.SerializerMethodField()
    reinsurance_scope_file = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = (
            'id',
            'name',
            'created',
            'modified',
            'location_file',
            'accounts_file',
            'reinsurance_info_file',
            'reinsurance_scope_file',
        )

    def create(self, validated_data):
        data = dict(validated_data)
        if not data.get('creator') and 'request' in self.context:
            data['creator'] = self.context.get('request').user
        return super(PortfolioSerializer, self).create(data)

    @swagger_serializer_method(serializer_or_field=LocFileSerializer)
    def get_location_file(self, instance):
        if not instance.location_file:
            return None
        else:
            request = self.context.get('request')
            return {
                "uri": instance.get_absolute_location_file_url(request=request),
                "name": instance.location_file.filename,
                "stored": str(instance.location_file.file)
            }

    @swagger_serializer_method(serializer_or_field=AccFileSerializer)
    def get_accounts_file(self, instance):
        if not instance.accounts_file:
            return None
        else:
            request = self.context.get('request')
            return {
                "uri": instance.get_absolute_accounts_file_url(request=request),
                "name": instance.accounts_file.filename,
                "stored": str(instance.accounts_file.file)
            }

    @swagger_serializer_method(serializer_or_field=ReinsInfoFileSerializer)
    def get_reinsurance_info_file(self, instance):
        if not instance.reinsurance_info_file:
            return None
        else:
            request = self.context.get('request')
            return {
                "uri": instance.get_absolute_reinsurance_info_file_url(request=request),
                "name": instance.reinsurance_info_file.filename,
                "stored": str(instance.reinsurance_info_file.file)
            }

    @swagger_serializer_method(serializer_or_field=ReinsScopeFileSerializer)
    def get_reinsurance_scope_file(self, instance):
        if not instance.reinsurance_scope_file:
            return None
        else:
            request = self.context.get('request')
            return {
                "uri": instance.get_absolute_reinsurance_scope_file_url(request=request),
                "name": instance.reinsurance_scope_file.filename,
                "stored": str(instance.reinsurance_scope_file.file)
            }


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
