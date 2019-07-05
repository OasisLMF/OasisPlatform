from rest_framework import serializers

from .models import DataFile
from ..analysis_models.models import  AnalysisModel

class ModelsSerializer(serializers.ModelSerializer):
    data_files = serializers.PrimaryKeyRelatedField(queryset=DataFile.objects.all(), many=True)

    class Meta:
        model = AnalysisModel
        fields = ('id')


class DataFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataFile
        linked_models = ModelsSerializer(many=True, read_only=False)
        fields = (
            'id',
            #'filename',
            'file_description',
            'created',
            'modified',
            'linked_models',
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
        rep['filename'] = instance.update_filename()
        rep['content_type'] = instance.update_content_type()
        return rep
