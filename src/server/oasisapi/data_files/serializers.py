from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from .models import DataFile


class DataFileSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()
    filename = serializers.SerializerMethodField()
    stored = serializers.SerializerMethodField()
    content_type = serializers.SerializerMethodField()

    class Meta:
        model = DataFile
        fields = (
            'id',
            'file_description',
            'created',
            'modified',
            'file',
            'filename',
            'stored',
            'content_type',
        )

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_data_file_url(request=request) if instance.file else None

    def get_filename(self, instance):
        return instance.get_filename()

    def get_stored(self, instance):
        return instance.get_filestore()

    def get_content_type(self, instance):
        return instance.get_content_type()

    def create(self, validated_data):
        data = dict(validated_data)
        # file_rsp = handle_related_file(self.get_object(), 'file', request, None)
        if not data.get('creator') and 'request' in self.context:
            data['creator'] = self.context.get('request').user
        return super(DataFileSerializer, self).create(data)
