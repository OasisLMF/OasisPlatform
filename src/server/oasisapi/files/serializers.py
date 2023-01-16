import logging
import hashlib
import io

import pandas as pd
from ods_tools.oed.exposure import OedExposure

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

from .models import RelatedFile

logger = logging.getLogger('root')


CONTENT_TYPE_MAPPING = {
    # Windows commonly reports CSVs as Excel files: https://www.christianwood.net/csv-file-upload-validation/
    'application/vnd.ms-excel': 'text/csv'
}


EXPOSURE_ARGS = {
    'accounts_file': 'account',
    'location_file': 'location',
    'reinsurance_info_file': 'ri_info',
    'reinsurance_scope_file': 'ri_scope'
}



def md5_filehash(in_memory_file, chunk_size=4096):
    hasher_md5 = hashlib.md5()
    for chunk in iter(lambda: in_memory_file.read(chunk_size), b""):
        hasher_md5.update(chunk)
    in_memory_file.seek(0)
    return hasher_md5.hexdigest()


class RelatedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelatedFile
        fields = (
            'created',
            'file',
            'filename',
            # 'filehash_md5',
        )

    def __init__(self, *args, content_types=None, parquet_storage=False, field=None, **kwargs):
        self.content_types = content_types or []
        self.parquet_storage = parquet_storage
        self.oed_field = field
        super(RelatedFileSerializer, self).__init__(*args, **kwargs)

    def validate(self, attrs):
        oed_validate = True   # This will be a setting.py option

        # TODO: Skil if field not in EXPOSURE_ARGS
        # TODO: add 'validate' url param to force validation on upload
        # TODO: Need to check content type to select either `read_csv` or `read_parquet`

        if oed_validate:
            VALIDATION_CONFIG = [
                {'name': 'required_fields', 'on_error': 'return'},
                {'name': 'unknown_column', 'on_error': 'return'},
                {'name': 'valid_values', 'on_error': 'return'},
                {'name': 'perils', 'on_error': 'return'},
                {'name': 'occupancy_code', 'on_error': 'return'},
                {'name': 'construction_code', 'on_error': 'return'},
                {'name': 'country_and_area_code', 'on_error': 'return'},
            ]

            uploaded_exposure = OedExposure(**{
                EXPOSURE_ARGS[self.oed_field]: pd.read_csv(io.BytesIO(attrs['file'].read())),
                'validation_config': VALIDATION_CONFIG
            })
            oed_validation_errors = uploaded_exposure.check()
            if len(oed_validation_errors) > 0:
                raise ValidationError([(error['name'], error['msg']) for error in oed_validation_errors])

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
        attrs['oed_validated'] = oed_validate
        # attrs['filehash_md5'] = md5_filehash(self.context['request'].FILES['file'])
        return super(RelatedFileSerializer, self).validate(attrs)

    def validate_file(self, value):
        mapped_content_type = CONTENT_TYPE_MAPPING.get(value.content_type, value.content_type)
        if self.content_types and mapped_content_type not in self.content_types:
            raise ValidationError('File should be one of [{}]'.format(', '.join(self.content_types)))
        return value
