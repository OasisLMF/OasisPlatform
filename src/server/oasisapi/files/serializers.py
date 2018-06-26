from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import RelatedFile


class RelatedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelatedFile
        fields = (
            'created',
            'file',
        )

    def __init__(self, *args, content_types=None, **kwargs):
        self.content_types = content_types or []
        super(RelatedFileSerializer, self).__init__(*args, **kwargs)

    def validate(self, attrs):
        attrs['creator'] = self.context['request'].user
        attrs['content_type'] = attrs['file'].content_type

        return super(RelatedFileSerializer, self).validate(attrs)

    def validate_file(self, value):
        if self.content_types and value.content_type not in self.content_types:
            raise ValidationError('File should be one of [{}]'.format(', '.join(self.content_types)))

        return value
