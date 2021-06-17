from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from .models import DataFile


class DataFileListSerializer(serializers.Serializer):
    """ Read Only DataFile Deserializer for efficiently returning a list of all
        DataFile from DB
    """

    # model fields 
    id = serializers.IntegerField(read_only=True)
    file_description = serializers.CharField(read_only=True)
    file_category = serializers.CharField(read_only=True)
    created = serializers.DateTimeField(read_only=True)
    modified = serializers.DateTimeField(read_only=True)

    # File fields 
    file = serializers.SerializerMethodField(read_only=True)
    filename = serializers.SerializerMethodField(read_only=True)
    stored = serializers.SerializerMethodField(read_only=True)
    content_type = serializers.SerializerMethodField(read_only=True)

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_data_file_url(request=request) if instance.file_id else None

    def get_filename(self, instance):
        return instance.get_filename()

    def get_stored(self, instance):
        return instance.get_filestore()

    def get_content_type(self, instance):
        return instance.get_content_type()


"""
 {
    "id": 1,
    "file_description": "1",
    "file_category": "string",
    "created": "2021-06-17T08:39:18.326853Z",
    "modified": "2021-06-17T08:39:18.326853Z",
    "file": "http://localhost:8000/v1/data_files/1/content/",
    "filename": "analysis_1_output.tar",
    "stored": "f3ab4e2714af4a11b992f94c243dfc86.tar",
    "content_type": "application/x-tar"
  },
  {
    "id": 2,
    "file_description": "2",
    "file_category": "string",
    "created": "2021-06-17T08:39:22.688895Z",
    "modified": "2021-06-17T08:39:22.688895Z",
    "file": "http://localhost:8000/v1/data_files/2/content/",
    "filename": "analysis_2_output.tar",
    "stored": "1c4ae3bae756433cb45b6c4e50849c44.tar",
    "content_type": "application/x-tar"
  },
"""

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
            'file_category',
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
