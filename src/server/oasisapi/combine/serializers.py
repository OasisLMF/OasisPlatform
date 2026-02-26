__all__ = [
    'CombineSettingSerializer'
]

from rest_framework import serializers
from ..schemas.serializers import (
    JsonSettingsSerializer,
    load_json_schema,
)

from ods_tools.combine.combine import CombineSettingsSchema


class CombineSettingSerializer(JsonSettingsSerializer):
    class Meta:
        swagger_schema_fields = load_json_schema(
            schema=CombineSettingsSchema().schema,
            link_prefix='#/definitions/CombineSettings'
        )

    def __init__(self, *args, **kwargs):
        super(CombineSettingSerializer, self).__init__(*args, **kwargs)
        self.filename = 'combine_settings.json'
        self.schemaClass = CombineSettingsSchema()

    def validate(self, data):
        return super(CombineSettingSerializer, self).validate_json(data)


class CombineAnalysesSerializer(serializers.Serializer):
    analysis_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True
    )

    config = CombineSettingSerializer(required=True)

    name = serializers.CharField(required=False, default='combine-analysis')
