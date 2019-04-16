import logging

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import RelatedFile

logger = logging.getLogger('root')


CONTENT_TYPE_MAPPING = {
    # Windows commonly reports CSVs as Excel files: https://www.christianwood.net/csv-file-upload-validation/
    'application/vnd.ms-excel': 'text/csv'
}


class RelatedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelatedFile
        fields = (
            'created',
            'file',
            'filename',
        )

    def __init__(self, *args, content_types=None, **kwargs):
        self.content_types = content_types or []
        super(RelatedFileSerializer, self).__init__(*args, **kwargs)

    def validate(self, attrs):
        attrs['creator'] = self.context['request'].user
        attrs['content_type'] = attrs['file'].content_type
        attrs['filename'] = self.context['request'].FILES['file']

        return super(RelatedFileSerializer, self).validate(attrs)

    def validate_file(self, value):
        mapped_content_type = CONTENT_TYPE_MAPPING.get(value.content_type, value.content_type)
        if self.content_types and value.content_type not in self.content_types and mapped_content_type not in self.content_types:
            raise ValidationError('File should be one of [{}]'.format(', '.join(self.content_types)))

        return value
