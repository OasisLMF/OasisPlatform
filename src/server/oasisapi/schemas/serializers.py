__all__ = [
    'StorageLinkSerializer'
    'LocFileSerializer',
    'AccFileSerializer',
    'ReinsInfoFileSerializer',
    'ReinsScopeFileSerializer',
    'AnalysisSettingsSerializer',
    'ModelParametersSerializer',
]

import json

from rest_framework import serializers

# import jsonschema
from jsonschema.exceptions import ValidationError as JSONSchemaValidationError
from jsonschema.exceptions import SchemaError as JSONSchemaError

from ods_tools.oed.setting_schema import ModelSettingSchema, AnalysisSettingSchema
from ods_tools.oed.common import OdsException


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


class LocFileSerializer(serializers.Serializer):
    uri = serializers.URLField()
    name = serializers.CharField()
    stored = serializers.CharField()

    def create(self, validated_data):
        raise NotImplementedError()

    def update(self, instance, validated_data):
        raise NotImplementedError()


class AccFileSerializer(serializers.Serializer):
    uri = serializers.URLField()
    name = serializers.CharField()
    stored = serializers.CharField()

    def create(self, validated_data):
        raise NotImplementedError()

    def update(self, instance, validated_data):
        raise NotImplementedError()


class ReinsInfoFileSerializer(serializers.Serializer):
    uri = serializers.URLField()
    name = serializers.CharField()
    stored = serializers.CharField()

    def create(self, validated_data):
        raise NotImplementedError()

    def update(self, instance, validated_data):
        raise NotImplementedError()


class ReinsScopeFileSerializer(serializers.Serializer):
    uri = serializers.URLField()
    name = serializers.CharField()
    stored = serializers.CharField()

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
    class Meta:
        swagger_schema_fields = load_json_schema(
            schema=ModelSettingSchema().schema,
            link_prefix='#/definitions/ModelSettings'
        )

    def __init__(self, *args, **kwargs):
        super(ModelParametersSerializer, self).__init__(*args, **kwargs)
        self.filenmame = 'model_settings.json'  # Store POSTED JSON using this fname
        self.schemaClass = ModelSettingSchema()

    def validate(self, data):
        return super(ModelParametersSerializer, self).validate_json(data)


class AnalysisSettingsSerializer(JsonSettingsSerializer):
    class Meta:
        swagger_schema_fields = load_json_schema(
            schema=AnalysisSettingSchema().schema,
            link_prefix='#/definitions/AnalysisSettings'
        )

    def __init__(self, *args, **kwargs):
        super(AnalysisSettingsSerializer, self).__init__(*args, **kwargs)
        self.filenmame = 'analysis_settings.json'  # Store POSTED JSON using this fname
        self.schemaClass = AnalysisSettingSchema()

    def validate(self, data):

        # Note: Workaround for to support workers 1.15.x and older. With the analysis settings schema change the workers with fail
        # These are added into existing files as a 'fix' so older workers can run without patching the worker schema
        # This *SHOULD* be removed at a later date once older models are not longer used
        data = self.schemaClass.compatibility(data)
        compatibility_field_map = {
            "module_supplier_id": {
                "updated_to": "model_supplier_id"
            },
            "model_version_id": {
                "updated_to": "model_name_id"
            },
        }
        for key in compatibility_field_map:
            if key not in data:
                data[key] = data[compatibility_field_map[key]['updated_to']]

        return super(AnalysisSettingsSerializer, self).validate_json(data)
