_all__ = [
    'HEALTHCHECK',
    'TOKEN_REFRESH_HEADER',
    'LocFileSerializer',
    'AccFileSerializer',
    'ReinsInfoFileSerializer',
    'ReinsScopeFileSerializer',
]

#from drf_yasg.openapi import Schema, Parameter, IN_HEADER
from drf_yasg import openapi
from drf_yasg.openapi import Schema

from rest_framework import serializers

HEALTHCHECK = Schema(
    title='HealthCheck',
    type='object',  
    properties={
        "status": Schema(title='status', read_only=True, type='string', enum= ['OK'])
    }
)

TOKEN_REFRESH_HEADER = openapi.Parameter('authorization', 'header', description="Refresh Token", type='string', default='Bearer <refresh_token>')


class TokenObtainPairResponseSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(read_only=True)
    access_token = serializers.CharField(read_only=True)
    token_type = serializers.CharField(read_only=True, default="Bearer")
    expires_in = serializers.IntegerField(read_only=True, default=86400)

    def create(self, validated_data):
        raise NotImplementedError()
    def update(self, instance, validated_data):
        raise NotImplementedError()


class TokenRefreshResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    token_type = serializers.CharField()
    expires_in = serializers.IntegerField()

    def create(self, validated_data):
        raise NotImplementedError()
    def update(self, instance, validated_data):
        raise NotImplementedError()


class LocFileSerializer(serializers.Serializer):
    url = serializers.URLField()
    name = serializers.CharField()
    Stored = serializers.CharField()

    def create(self, validated_data):
        raise NotImplementedError()
    def update(self, instance, validated_data):
        raise NotImplementedError()

class AccFileSerializer(serializers.Serializer):
    url = serializers.URLField()
    name = serializers.CharField()
    Stored = serializers.CharField()

    def create(self, validated_data):
        raise NotImplementedError()
    def update(self, instance, validated_data):
        raise NotImplementedError()

class ReinsInfoFileSerializer(serializers.Serializer):
    url = serializers.URLField()
    name = serializers.CharField()
    Stored = serializers.CharField()

    def create(self, validated_data):
        raise NotImplementedError()
    def update(self, instance, validated_data):
        raise NotImplementedError()

class ReinsScopeFileSerializer(serializers.Serializer):
    url = serializers.URLField()
    name = serializers.CharField()
    Stored = serializers.CharField()

    def create(self, validated_data):
        raise NotImplementedError()
    def update(self, instance, validated_data):
        raise NotImplementedError()
