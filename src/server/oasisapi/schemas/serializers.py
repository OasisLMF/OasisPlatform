__all__ = [
    'LocFileSerializer',
    'AccFileSerializer',
    'ReinsInfoFileSerializer',
    'ReinsScopeFileSerializer',
    'AnalysisSettingsSerializer',
    'ModelResourceSerializer',
]

import io
import os
import json 

from rest_framework import serializers

from jsonschema import validate  
from jsonschema.exceptions import ValidationError as JSONSchemaValidationError
from jsonschema.exceptions import SchemaError as JSONSchemaError

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


class ModelResourceSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = load_json_schema('model_resource.json')

    def __init__(self, *args, **kwargs):
        super(ModelResourceSerializer, self).__init__(*args, **kwargs)
        self.filenmame = 'model_settings.json'
        self.schema = load_json_schema('model_resource.json')

    def to_internal_value(self, data):
        return data

    def validate(self, data):
        try:
            validate(data, self.schema)
        except JSONSchemaValidationError as e:
            raise serializers.ValidationError(e.message)
        return self.to_internal_value(json.dumps(data))
        

class AnalysisSettingsSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = load_json_schema('analysis_settings.json')

    def __init__(self, *args, **kwargs):
        super(AnalysisSettingsSerializer, self).__init__(*args, **kwargs)
        self.filenmame = 'analysis_settings.json'
        self.schema = load_json_schema('analysis_settings.json')

    def to_internal_value(self, data):
        return data

    def validate(self, data):
        try:
            validate(data, self.schema)
        except (JSONSchemaValidationError, JSONSchemaError) as e:
            raise serializers.ValidationError(e.message)
        return self.to_internal_value(json.dumps(data))
