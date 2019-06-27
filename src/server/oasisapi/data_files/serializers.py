from rest_framework import serializers

from .models import DataFile


class DataFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataFile
        fields = (
            'id',
            'file_name',
            'file_description',
            'created',
            'modified',
        )

    def create(self, validated_data):
        data = dict(validated_data)
        if not data.get('creator') and 'request' in self.context:
            data['creator'] = self.context.get('request').user
        return super(DataFileSerializer, self).create(data)

    def to_representation(self, instance):
        rep = super(DataFileSerializer, self).to_representation(instance)

        request = self.context.get('request')

        rep['data_file'] = instance.get_absolute_data_file_url(request=request) if instance.data_file else None

        return rep
