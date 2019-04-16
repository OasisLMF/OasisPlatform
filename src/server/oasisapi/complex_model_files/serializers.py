from rest_framework import serializers

from .models import ComplexModelDataFile


class ComplexModelDataFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplexModelDataFile
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
        return super(ComplexModelDataFileSerializer, self).create(data)

    def to_representation(self, instance):
        rep = super(ComplexModelDataFileSerializer, self).to_representation(instance)

        request = self.context.get('request')

        rep['data_file'] = instance.get_absolute_data_file_url(request=request) if instance.data_file else None

        return rep
