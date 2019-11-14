__all__ = [
    'FILE_RESPONSE',
    'HEALTHCHECK',
    'TOKEN_REFRESH_HEADER',
    'LocFileSerializer',
    'AccFileSerializer',
    'ReinsInfoFileSerializer',
    'ReinsScopeFileSerializer',
    'load_json_schema'
]

import io
import json
import os

from drf_yasg import openapi
from drf_yasg.openapi import Schema

from rest_framework import serializers


FILE_RESPONSE = openapi.Response(
    'File Download',
    schema=Schema(type=openapi.TYPE_FILE),
    headers={
        "Content-Disposition": {
            "description": "filename",
            "type": openapi.TYPE_STRING,
            "default": 'attachment; filename="<FILE>"'
        },
        "Content-Type": {
            "description": "mime type",
            "type": openapi.TYPE_STRING
        },

    })

HEALTHCHECK = Schema(
    title='HealthCheck',
    type='object',
    properties={
        "status": Schema(title='status', read_only=True, type='string', enum=['OK'])
    }
)

TOKEN_REFRESH_HEADER = openapi.Parameter(
    'authorization',
    'header',
    description="Refresh Token",
    type='string',
    default='Bearer <refresh_token>'
)


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


def load_json_schema(json_schema_file):
    """
        Load json schema stored in the .schema dir
    """
    schema_dir = os.path.dirname(os.path.abspath(__file__))
    schema_fp = os.path.join(schema_dir, json_schema_file)
    with io.open(schema_fp, 'r', encoding='utf-8') as f:
        return json.load(f)


# Create an analysis_settings sersialzer

### https://github.com/axnsan12/drf-yasg/issues/396
### https://github.com/wework/json-schema-to-openapi-schema
### https://richardtier.com/2014/03/24/json-schema-validation-with-django-rest-framework/
