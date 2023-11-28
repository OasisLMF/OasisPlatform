from django.contrib.auth.models import Group
from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from ..models import DataFile
from ...permissions.group_auth import validate_and_update_groups


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
    groups = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')

    # File fields
    file = serializers.SerializerMethodField(read_only=True)
    filename = serializers.SerializerMethodField(read_only=True)
    stored = serializers.SerializerMethodField(read_only=True)
    content_type = serializers.SerializerMethodField(read_only=True)

    class Meta:
        ref_name =  "v2_" + __qualname__.split('.')[0]


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


class DataFileSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()
    filename = serializers.SerializerMethodField()
    stored = serializers.SerializerMethodField()
    content_type = serializers.SerializerMethodField()
    groups = serializers.SlugRelatedField(many=True, read_only=False, slug_field='name', required=False, queryset=Group.objects.all())

    class Meta:
        ref_name =  "v2_" + __qualname__.split('.')[0]
        model = DataFile
        fields = (
            'id',
            'file_description',
            'file_category',
            'created',
            'modified',
            'groups',
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

    def validate(self, attrs):
        # Validate and update groups parameter
        validate_and_update_groups(self.partial, self.context.get('request').user, attrs)

        return attrs

    def create(self, validated_data):
        data = dict(validated_data)
        # file_rsp = handle_related_file(self.get_object(), 'file', request, None)
        if not data.get('creator') and 'request' in self.context:
            data['creator'] = self.context.get('request').user
        return super(DataFileSerializer, self).create(data)
