from os import path
from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files import File
from django.core.files.base import ContentFile
from botocore.exceptions import ClientError as S3_ClientError

from ..analyses.serializers import AnalysisSerializer
from ..files.models import file_storage_link
from ..files.models import RelatedFile
from .models import Portfolio


from ..schemas.serializers import (
    LocFileSerializer,
    AccFileSerializer,
    ReinsInfoFileSerializer,
    ReinsScopeFileSerializer,
)


class PortfolioSerializer(serializers.ModelSerializer):
    accounts_file = serializers.SerializerMethodField()
    location_file = serializers.SerializerMethodField()
    reinsurance_info_file = serializers.SerializerMethodField()
    reinsurance_scope_file = serializers.SerializerMethodField()
    storage_links = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = (
            'id',
            'name',
            'created',
            'modified',
            'location_file',
            'accounts_file',
            'reinsurance_info_file',
            'reinsurance_scope_file',
            'storage_links',
        )

    def create(self, validated_data):
        data = dict(validated_data)
        if not data.get('creator') and 'request' in self.context:
            data['creator'] = self.context.get('request').user
        return super(PortfolioSerializer, self).create(data)

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_storage_links(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_storage_url(request=request)

    @swagger_serializer_method(serializer_or_field=LocFileSerializer)
    def get_location_file(self, instance):
        if not instance.location_file:
            return None
        else:
            request = self.context.get('request')
            return {
                "uri": instance.get_absolute_location_file_url(request=request),
                "name": instance.location_file.filename,
                "stored": str(instance.location_file.file)
            }

    @swagger_serializer_method(serializer_or_field=AccFileSerializer)
    def get_accounts_file(self, instance):
        if not instance.accounts_file:
            return None
        else:
            request = self.context.get('request')
            return {
                "uri": instance.get_absolute_accounts_file_url(request=request),
                "name": instance.accounts_file.filename,
                "stored": str(instance.accounts_file.file)
            }

    @swagger_serializer_method(serializer_or_field=ReinsInfoFileSerializer)
    def get_reinsurance_info_file(self, instance):
        if not instance.reinsurance_info_file:
            return None
        else:
            request = self.context.get('request')
            return {
                "uri": instance.get_absolute_reinsurance_info_file_url(request=request),
                "name": instance.reinsurance_info_file.filename,
                "stored": str(instance.reinsurance_info_file.file)
            }

    @swagger_serializer_method(serializer_or_field=ReinsScopeFileSerializer)
    def get_reinsurance_scope_file(self, instance):
        if not instance.reinsurance_scope_file:
            return None
        else:
            request = self.context.get('request')
            return {
                "uri": instance.get_absolute_reinsurance_scope_file_url(request=request),
                "name": instance.reinsurance_scope_file.filename,
                "stored": str(instance.reinsurance_scope_file.file)
            }


class PortfolioStorageSerializer(serializers.ModelSerializer):
    accounts_file = serializers.SerializerMethodField()
    location_file = serializers.SerializerMethodField()
    reinsurance_info_file = serializers.SerializerMethodField()
    reinsurance_scope_file = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = (
            'location_file',
            'accounts_file',
            'reinsurance_info_file',
            'reinsurance_scope_file',
        )

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_location_file(self, instance):
        return file_storage_link(instance.location_file, True)

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_accounts_file(self, instance):
        return file_storage_link(instance.accounts_file, True)

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_reinsurance_info_file(self, instance):
        return file_storage_link(instance.reinsurance_info_file, True)

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_reinsurance_scope_file(self, instance):
        return file_storage_link(instance.reinsurance_scope_file, True)

    def is_in_storage(self, value):
        if not hasattr(default_storage, 'bucket'):
            return default_storage.exists(value)
        else:
            try:
                default_storage.bucket.Object(value).load()
                return True
            except S3_ClientError as e:
                if e.response['Error']['Code'] == "404":
                    return False
                else:
                    raise e

    def validate(self, attrs):
        file_keys = [k for k in self.fields.keys()]

        # Check for at least one entry
        file_values = [v for k, v in self.initial_data.items() if k in file_keys]
        if len(file_values) == 0:
            raise serializers.ValidationError('At least one file field reference required from [{}]'.format(', '.join(file_keys)))

        errors = dict()
        for k in file_keys:
            value = self.initial_data.get(k)
            if value is not None:

                # Check type is string
                if not isinstance(value, str):
                    errors[k] = "Value is not type string, found {}".format(type(value))
                    continue
                # Check String is not empry
                elif len(value.strip()) < 1:
                    errors[k] = "Value is emtpry or whitespace string."
                    continue
                # Check that the file exisits
                elif not self.is_in_storage(value):
                    errors[k] = "File '{}' not found in default storage".format(value)
                    continue

                # Data is valid
                attrs[k] = value
        if errors:
            raise serializers.ValidationError(errors)
        return super(PortfolioStorageSerializer, self).validate(attrs)

    def update(self, instance, validated_data):
        files_for_removal = list()
        content_type = 'text/csv'
        for field in validated_data:

            # S3 storage - File copy needed
            if hasattr(default_storage, 'bucket'):
                fname = path.basename(validated_data[field])
                new_file = ContentFile('')
                new_file.name = default_storage.get_alternative_name(fname, '')
                new_related_file = RelatedFile.objects.create(
                    file=new_file,
                    filename=fname,
                    content_type=content_type,
                    creator=self.context['request'].user,
                    store_as_filename=True,
                )
                bucket = default_storage.bucket
                stored_file = default_storage.open(new_related_file.file.name)
                stored_file.obj.copy({"Bucket": bucket.name, "Key": validated_data[field]})

            # Shared-fs
            else:
                stored_file = default_storage.open(validated_data[field])
                new_file = File(stored_file, name=validated_data[field])
                new_related_file = RelatedFile.objects.create(
                    file=new_file,
                    filename=validated_data[field],
                    content_type=content_type,
                    creator=self.context['request'].user,
                    store_as_filename=True,
                )

            # Mark prev ref for deleation if it exisits
            if hasattr(instance, field):
                prev_file = getattr(instance, field)
                if prev_file:
                    files_for_removal.append(prev_file)

            # Set new file ref
            setattr(instance, field, new_related_file)

        # Update & Delete prev linked files
        instance.save(update_fields=[k for k in validated_data])
        for f in files_for_removal:
            f.delete()
        return instance


class CreateAnalysisSerializer(AnalysisSerializer):
    class Meta(AnalysisSerializer.Meta):
        fields = ['name', 'model']

    def __init__(self, portfolio=None, *args, **kwargs):
        self.portfolio = portfolio
        super(CreateAnalysisSerializer, self).__init__(*args, **kwargs)

    def validate(self, attrs):
        attrs['portfolio'] = self.portfolio
        if not self.portfolio.location_file:
            raise ValidationError({'portfolio': '"location_file" must not be null'})

        return attrs

    def create(self, validated_data):
        data = dict(validated_data)
        if 'request' in self.context:
            data['creator'] = self.context.get('request').user
        return super(CreateAnalysisSerializer, self).create(data)
