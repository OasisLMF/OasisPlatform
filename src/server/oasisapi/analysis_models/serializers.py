from drf_yasg.utils import swagger_serializer_method
from django.core.files import File
from rest_framework import serializers

from .models import AnalysisModel
from ..schemas.custom_swagger import load_json_schema

class AnalysisModelSerializer(serializers.ModelSerializer):
    resource_file = serializers.SerializerMethodField()
    resource_settings = serializers.SerializerMethodField()

    class Meta:
        model = AnalysisModel
        fields = (
            'id',
            'supplier_id',
            'model_id',
            'version_id',
            'created',
            'modified',
            'data_files',
            'resource_file',
            'resource_settings',
        )

    def create(self, validated_data):
        data = validated_data.copy()
        if 'request' in self.context:
            data['creator'] = self.context.get('request').user
        return super(AnalysisModelSerializer, self).create(data)

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_resource_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_resources_file_url(request=request)
    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_resource_settings(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_resources_settings_url(request=request)



# -------------------------------------------------------------------------------
import json

from jsonschema import validate  
from jsonschema.exceptions import ValidationError as JSONSchemaValidationError

class ModelResourceSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = load_json_schema('model_resource.json')

    def __init__(self, *args, **kwargs):
        super(ModelResourceSerializer, self).__init__(*args, **kwargs)
        self.filenmame = 'model_settings.json'
        self.schema = load_json_schema('model_resource.json')

    def to_internal_value(self, data):
        return data

    #def to_internal_value(self, data):
    #    # write JSON to in memory file
    #    with open(self.filenmame, 'w') as f:
    #        in_memory_file = InMemoryUploadedFile(
    #            file=f, 
    #            field_name='file',
    #            name=self.filenmame,
    #            content_type='application/json',
    #            size=len(data.encode('utf-8')),
    #            charset=None
    #        )
    #        in_memory_file.write(data)

    #    query_dict = QueryDict('', mutable=True)
    #    query_dict.update({'file': in_memory_file})
    #    return query_dict
    
    def validate(self, data):
        try:
            validate(data, self.schema)
        except JSONSchemaValidationError as e:
            raise serializers.ValidationError(e.message)
        return self.to_internal_value(json.dumps(data))
