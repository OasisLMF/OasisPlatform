import hashlib
import logging
import io
from pathlib import Path

from drf_yasg.utils import swagger_serializer_method
from rest_framework.parsers import MultiPartParser

from ods_tools.oed.exposure import OedExposure
from ods_tools.oed.common import OdsException

from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.conf import settings as django_settings

from .models import RelatedFile, MappingFile

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


class MappingFileSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()
    input_validation_file = serializers.SerializerMethodField()
    output_validation_file = serializers.SerializerMethodField()

    class Meta:
        ref_name = None
        model = MappingFile
        fields = (
            'name',
            'description',
            'file',
            'input_validation_file',
            'output_validation_file',
        )

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_file(self, instance: MappingFile):
        request = self.context.get('request')
        return instance.get_absolute_conversion_file_url(request)

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_input_validation_file(self, instance: MappingFile):
        request = self.context.get('request')
        return instance.get_absolute_input_validation_file_url(request)

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_output_validation_file(self, instance: MappingFile):
        request = self.context.get('request')
        return instance.get_absolute_output_validation_file_url(request)


class ConvertSerializer(serializers.Serializer):
    mapping_file = serializers.CharField()


class RelatedFileSerializer(serializers.ModelSerializer):

    groups = serializers.SlugRelatedField(many=True, read_only=False, slug_field='name', required=False, queryset=Group.objects.all())
    mapping_file = serializers.PrimaryKeyRelatedField(queryset=MappingFile.objects.all(), required=False)

    class Meta:
        ref_name = None
        model = RelatedFile
        fields = (
            'created',
            'file',
            'converted_file',
            'filename',
            'groups',
            'mapping_file',
            'conversion_state',
            # 'filehash_md5',
        )

    def __init__(self, *args, content_types=None, parquet_storage=False, field=None, oed_validate=None, **kwargs):
        self.content_types = content_types or []
        self.parquet_storage = parquet_storage
        self.oed_field = field
        self.oed_validate = oed_validate if oed_validate is not None else django_settings.PORTFOLIO_UPLOAD_VALIDATION
        super(RelatedFileSerializer, self).__init__(*args, **kwargs)

    def validate(self, attrs):
        run_validation = self.oed_validate and self.oed_field in EXPOSURE_ARGS
        convert_to_parquet = self.parquet_storage and attrs['file'].content_type == 'text/csv'

        # Create dataframe from file upload
        if run_validation or convert_to_parquet:
            try:
                uploaded_exposure = OedExposure(**{
                    EXPOSURE_ARGS[self.oed_field]: attrs['file'],
                    'validation_config': django_settings.PORTFOLIO_VALIDATION_CONFIG
                })
            except OdsException as e:
                raise ValidationError('Failed to read exposure data, file is corrupted or set with incorrect format', e)

        # Run OED Validation
        if run_validation:
            oed_validation_errors = uploaded_exposure.check()
            if len(oed_validation_errors) > 0:
                raise ValidationError(detail=[(error['name'], error['msg']) for error in oed_validation_errors])

        # Convert 'CSV' upload to 'parquet'
        if convert_to_parquet:
            try:
                f = io.open(attrs['file'].name + '.parquet', 'wb+')
                exposure_file = getattr(uploaded_exposure, EXPOSURE_ARGS[self.oed_field])
                exposure_file.dataframe.to_parquet(f)
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
        attrs['oed_validated'] = self.oed_validate
        return super(RelatedFileSerializer, self).validate(attrs)

    def validate_file(self, value):
        mapped_content_type = CONTENT_TYPE_MAPPING.get(value.content_type, value.content_type)
        file_extention = Path(value.name).suffix[1:].lower()

        # check content_types is valid
        if self.content_types and mapped_content_type not in self.content_types:
            raise ValidationError('File should be one of [{}]'.format(', '.join(self.content_types)))

        # check content type matches file extention
        extention_mapping = {
            'parquet': 'application/octet-stream',
            'pq': 'application/octet-stream',
            'csv': 'text/csv',
            'gz': 'application/gzip',
            'zip': 'application/zip',
            'bz2': 'application/x-bzip2',
        }

        if file_extention in extention_mapping:
            if extention_mapping.get(file_extention) != mapped_content_type:
                raise ValidationError(
                    f"File extention '{file_extention}' mismatched with request header 'Content-Type': '{mapped_content_type}', should be set to '{extention_mapping.get(file_extention)}'")

        return value


class FileSQLSerializer(serializers.Serializer):
    sql = serializers.CharField()

    def validate_sql(self, value):
        # for purposes of validation, lowercase the sql, return the original
        sql_to_validate = value.lower()
        if "from table" not in sql_to_validate:
            raise serializers.ValidationError("The from clause of the SQL must be "
                                              "'FROM table', where table is explicitly the word table")

        # TODO what else can we validate here? No point sanitising further as the SQL is not against a
        # database which can be manipulated?

        return value


class NestedRelatedFileSerializer(serializers.ModelSerializer):
    sql = serializers.SerializerMethodField()

    class Meta:
        ref_name = None
        model = RelatedFile
        fields = (
            'id',
            'created',
            'file',
            'filename',
            'sql',
        )

    def __init__(self, *args, analyses=None, **kwargs):
        self.analyses = analyses
        super().__init__(*args, **kwargs)

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_sql(self, instance):
        request = self.context.get('request')

        return self.analyses.get_absolute_output_file_sql_url(request=request, file_pk=instance.id)
