from rest_framework import serializers

from .models import DataFile

class DataFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataFile
        fields = (
            'id',
            'file_description',
            'created',
            'modified',
        )

    def create(self, validated_data):
        data = dict(validated_data)
        #file_rsp = handle_related_file(self.get_object(), 'file', request, None)
        if not data.get('creator') and 'request' in self.context:
            data['creator'] = self.context.get('request').user
        return super(DataFileSerializer, self).create(data)

    

    def to_representation(self, instance):
        rep = super(DataFileSerializer, self).to_representation(instance)
        request = self.context.get('request')
        rep['file'] = instance.get_absolute_data_file_url(request=request) if instance.file else None
        rep['filename'] = instance.get_filename()
        rep['stored'] = instance.get_filestore()
        rep['content_type'] = instance.get_content_type()
        return rep
