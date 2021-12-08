import hashlib
import logging
import io
import ods_tools

from django.contrib.auth.models import Group
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

from .models import RelatedFile

logger = logging.getLogger('root')


CONTENT_TYPE_MAPPING = {
    # Windows commonly reports CSVs as Excel files: https://www.christianwood.net/csv-file-upload-validation/
    'application/vnd.ms-excel': 'text/csv'
}


def md5_filehash(in_memory_file, chunk_size=4096):
    hasher_md5 = hashlib.md5()
    for chunk in iter(lambda: in_memory_file.read(chunk_size), b""):
        hasher_md5.update(chunk)
    in_memory_file.seek(0)
    return hasher_md5.hexdigest()


class RelatedFileSerializer(serializers.ModelSerializer):

    groups = serializers.SlugRelatedField(many=True, read_only=False, slug_field='name', required=False, queryset=Group.objects.all())

    class Meta:
        model = RelatedFile
        fields = (
            'created',
            'file',
            'filename',
            'groups',
            # 'filehash_md5',
        )

    def __init__(self, *args, content_types=None, parquet_storage=False, **kwargs):
        self.content_types = content_types or []
        self.parquet_storage = parquet_storage
        super(RelatedFileSerializer, self).__init__(*args, **kwargs)

    def validate(self, attrs):
        # Covert to parquet if option is on and file is CSV
        if self.parquet_storage and attrs['file'].content_type == 'text/csv':
            try:
                attrs['file'].seek(0)
                temp_df = ods_tools.read_csv(io.BytesIO(attrs['file'].read()))

                # Create new UploadedFile object
                f = io.open(attrs['file'].name + '.parquet', 'wb+')
                temp_df.to_parquet(f)
                in_memory_file = UploadedFile(
                    file=f,
                    name=f.name,
                    content_type='application/octet-stream',
                    size=f.__sizeof__(),
                    charset=None
                )
                attrs['file'] = in_memory_file
            except Exception as e:
                raise ValidationError('Failed to covert file to parquet [{}]'.format(e))

        attrs['creator'] = self.context['request'].user
        attrs['content_type'] = attrs['file'].content_type
        attrs['filename'] = attrs['file'].name
        attrs['groups'] = self.context['request'].user.groups.all()
        # attrs['filehash_md5'] = md5_filehash(self.context['request'].FILES['file'])
        return super(RelatedFileSerializer, self).validate(attrs)

    def validate_file(self, value):
        mapped_content_type = CONTENT_TYPE_MAPPING.get(value.content_type, value.content_type)
        if self.content_types and mapped_content_type not in self.content_types:
            raise ValidationError('File should be one of [{}]'.format(', '.join(self.content_types)))
        return value
