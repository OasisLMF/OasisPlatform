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

def update_links(link_prefix, d):
    """
        Linking in pre-defined scheams with path links will be nested
        into the overall swagger schema, breaking preset links

        Remap based on 'link_prefix' value
            '#definitions/option' -> #definitions/SWAGGER_OBJECT/definitions/option

    """
    for k,v in d.items():
        if isinstance(v, dict):
            update_links(link_prefix, v)
        else:
            if k in '$ref':
                link = v.split('#')[-1]
                d[k] = "{}{}".format(link_prefix, link)

def load_json_schema(json_schema_file, link_prefix=None):
    """
        Load json schema stored in the .schema dir
    """
    schema_dir = os.path.dirname(os.path.abspath(__file__))
    schema_fp = os.path.join(schema_dir, json_schema_file)
    with io.open(schema_fp, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    if link_prefix:
        update_links(link_prefix, schema)
    return schema

class ModelResourceSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = load_json_schema(
            json_schema_file='model_resource.json',
            link_prefix='#/definitions/ModelResource'
        )        

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
        swagger_schema_fields = load_json_schema(
            json_schema_file='analysis_settings.json',
            link_prefix='#/definitions/AnalysisSettings'
        )        

    def __init__(self, *args, **kwargs):
        super(AnalysisSettingsSerializer, self).__init__(*args, **kwargs)
        self.filenmame = 'analysis_settings.json'
        self.schema = load_json_schema('analysis_settings.json')

    def to_internal_value(self, data):
        return data

    def validate(self, data):
        try:
            # check and strip away top-level
            if 'analysis_settings' in data:
                data = data['analysis_settings']

            validate(data, self.schema)
        except (JSONSchemaValidationError, JSONSchemaError) as e:
            raise serializers.ValidationError(e.message)
        return self.to_internal_value(json.dumps(data))
