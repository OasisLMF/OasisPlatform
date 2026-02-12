__all__ = [
    'StorageLinkSerializer',
    'InputFileSerializer',
    'AnalysisSettingsSerializer',
    'ModelParametersSerializer',
    'GroupNameSerializer',
    'QueueNameSerializer',
    'TaskCountSerializer',
    'TaskErrorSerializer',
]

import json

from rest_framework import serializers
from drf_spectacular.extensions import OpenApiSerializerExtension

# import jsonschema
from jsonschema.exceptions import ValidationError as JSONSchemaValidationError
from jsonschema.exceptions import SchemaError as JSONSchemaError

from ods_tools.oed import AnalysisSettingHandler, ModelSettingHandler
from ods_tools.oed.common import OdsException


TaskErrorSerializer = serializers.ListField(child=serializers.IntegerField())
GroupNameSerializer = serializers.ListField(child=serializers.CharField())
QueueNameSerializer = serializers.ListField(child=serializers.CharField())


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


class StorageLinkSerializer(serializers.Serializer):
    accounts_file = serializers.CharField()
    location_file = serializers.CharField()
    reinsurance_info_file = serializers.CharField()
    reinsurance_scope_file = serializers.CharField()

    def create(self, validated_data):
        raise NotImplementedError()

    def update(self, instance, validated_data):
        raise NotImplementedError()


class InputFileSerializer(serializers.Serializer):
    uri = serializers.URLField()
    name = serializers.CharField()
    stored = serializers.CharField()
    converted_uri = serializers.URLField()
    converted_stored = serializers.CharField()
    conversion_state = serializers.CharField()

    def create(self, validated_data):
        raise NotImplementedError()

    def update(self, instance, validated_data):
        raise NotImplementedError()


class TaskCountSerializer(serializers.Serializer):
    TOTAL_IN_QUEUE = serializers.IntegerField()
    TOTAL = serializers.IntegerField()
    PENDING = serializers.IntegerField()
    QUEUED = serializers.IntegerField()
    STARTED = serializers.IntegerField()
    COMPLETED = serializers.IntegerField()
    CANCELLED = serializers.IntegerField()
    ERROR = serializers.IntegerField()

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
    for k, v in d.items():
        if isinstance(v, dict):
            update_links(link_prefix, v)
        elif isinstance(v, list):
            for el in v:
                if isinstance(el, dict):
                    update_links(link_prefix, el)
        else:
            if k in '$ref':
                link = v.split('#')[-1]
                d[k] = "{}{}".format(link_prefix, link)


def load_json_schema(schema, link_prefix=None):
    """
        Load json schema stored in the .schema dir
    """
    if link_prefix:
        update_links(link_prefix, schema)
    return schema


class JsonSettingsSerializer(serializers.Serializer):

    def to_internal_value(self, data):
        return data

    def validate_json(self, data):
        try:
            vaild, errors = self.schemaClass.validate(data, raise_error=False)
            if not vaild:
                raise serializers.ValidationError(errors)
        except (JSONSchemaValidationError, JSONSchemaError, OdsException) as e:
            raise serializers.ValidationError(e.message)
        return self.to_internal_value(json.dumps(data))


class ModelParametersSerializer(JsonSettingsSerializer):

    def __init__(self, *args, **kwargs):
        super(ModelParametersSerializer, self).__init__(*args, **kwargs)
        self.filename = 'model_settings.json'  # Store POSTED JSON using this fname
        self.schemaClass = ModelSettingHandler.make()

    def validate(self, data):
        return super(ModelParametersSerializer, self).validate_json(data)


class AnalysisSettingsSerializer(JsonSettingsSerializer):

    def __init__(self, *args, **kwargs):
        super(AnalysisSettingsSerializer, self).__init__(*args, **kwargs)
        self.filename = 'analysis_settings.json'  # Store POSTED JSON using this fname
        self.schemaClass = AnalysisSettingHandler.make()

    def validate(self, data):
        # Note: Workaround for to support workers 1.15.x and older. With the analysis settings schema change the workers with
        # These are added into existing files as a 'fix' so older workers can run without patching the worker schema
        compatibility_fields = [
            ("module_supplier_id", "model_supplier_id"),
            ("model_version_id", "model_name_id"),
        ]
        for old_key, new_key in compatibility_fields:
            if old_key in data and new_key not in data:
                data[new_key] = data[old_key]
            if new_key in data and old_key not in data:
                data[old_key] = data[new_key]

        return super(AnalysisSettingsSerializer, self).validate_json(data)


def _sanitize_json_schema_for_openapi(schema):
    """Strip JSON Schema features that are not valid in OpenAPI 3.0.3.

    OpenAPI 3.0 uses a restricted subset of JSON Schema. Attributes like $schema,
    definitions, patternProperties, and unevaluatedProperties are not supported.
    Also, 'type' must be a string (not an array like ["integer", "string"]).

    Since 'definitions' are stripped, any '$ref' pointers into them become dangling.
    Replace objects containing '$ref' with 'type: object' so code generators
    don't emit references to non-existent types.

    'additionalProperties' and 'minProperties' are stripped because ods_tools
    schemas place them on array types (invalid in OA3) and code generators
    produce broken validation code for them. Runtime validation is handled
    by ods_tools in Python.
    """
    # Keys that exist in JSON Schema but not in OA3 Schema Objects
    unsupported_keys = {'$schema', 'definitions', 'definition', 'patternProperties', 'unevaluatedProperties'}
    # Keys that confuse code generators when placed on inline schemas (only used
    # for JSON Schema validation which ods_tools handles in Python at runtime)
    generator_problematic_keys = {'additionalProperties', 'minProperties'}

    if isinstance(schema, dict):
        # If this dict is just a $ref, replace with a generic object
        if '$ref' in schema:
            return {'type': 'object'}

        cleaned = {}
        for key, value in schema.items():
            if key in unsupported_keys:
                continue
            if key in generator_problematic_keys:
                continue
            if key == 'type' and isinstance(value, list):
                # OA3 type must be a string; use oneOf for multi-type
                cleaned['oneOf'] = [{'type': t} for t in value]
            else:
                cleaned[key] = _sanitize_json_schema_for_openapi(value)
        return cleaned
    elif isinstance(schema, list):
        return [_sanitize_json_schema_for_openapi(item) for item in schema]
    return schema


class _JsonSettingsSchemaExtension(OpenApiSerializerExtension):
    """Return the raw JSON schema from ods_tools for ModelParametersSerializer and AnalysisSettingsSerializer."""
    target_class = 'src.server.oasisapi.schemas.serializers.JsonSettingsSerializer'
    match_subclasses = True

    def map_serializer(self, auto_schema, direction):
        if isinstance(self.target, ModelParametersSerializer) or self.target.__class__ is ModelParametersSerializer:
            schema = load_json_schema(
                schema=ModelSettingHandler.make().get_schema('model_settings_schema'),
                link_prefix='#/components/schemas/ModelSettings',
            )
        elif isinstance(self.target, AnalysisSettingsSerializer) or self.target.__class__ is AnalysisSettingsSerializer:
            schema = load_json_schema(
                schema=AnalysisSettingHandler.make().get_schema('analysis_settings_schema'),
                link_prefix='#/components/schemas/AnalysisSettings',
            )
        else:
            schema = {'type': 'object'}
        return _sanitize_json_schema_for_openapi(schema)
