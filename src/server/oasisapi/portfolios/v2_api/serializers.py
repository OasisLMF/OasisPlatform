from os import path
import mimetypes

from botocore.exceptions import ClientError as S3_ClientError
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from azure.core.exceptions import ResourceNotFoundError as Blob_ResourceNotFoundError
from azure.storage.blob import BlobLeaseClient
from ..models import Portfolio
from ...analyses.v2_api.serializers import AnalysisSerializer
from ...files.models import RelatedFile
from ...files.models import file_storage_link
from ...files.upload import wait_for_blob_copy
from ...permissions.group_auth import validate_and_update_groups, validate_user_is_owner
from ...schemas.serializers import (
    InputFileSerializer,
)


def _serialize_input_file(file_obj, abs_uri, request):
    if not file_obj:
        return None
    else:
        converted = (
            file_obj.conversion_state == RelatedFile.ConversionState.DONE and
            file_obj.converted_file
        )
        return {
            "uri": abs_uri,
            "name": file_obj.filename,
            "stored": str(file_obj.file),
            "converted_uri": abs_uri + "?converted" if converted else None,
            "converted_stored": str(file_obj.converted_file) if converted else None,
            "conversion_state": file_obj.conversion_state,
            "conversion_log_fie": file_obj.get_absolute_conversion_log_file_url(request, namespace="v2-files"),
        }


class PortfolioListSerializer(serializers.Serializer):
    """ Read Only Portfolio Deserializer for efficiently returning a list of all
        Portfolios in DB
    """
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    created = serializers.DateTimeField(read_only=True)
    modified = serializers.DateTimeField(read_only=True)
    accounts_file = serializers.SerializerMethodField(read_only=True)
    location_file = serializers.SerializerMethodField(read_only=True)
    reinsurance_info_file = serializers.SerializerMethodField(read_only=True)
    reinsurance_scope_file = serializers.SerializerMethodField(read_only=True)
    storage_links = serializers.SerializerMethodField(read_only=True)
    groups = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_storage_links(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_storage_url(request=request, namespace="v2-portfolios")

    @swagger_serializer_method(serializer_or_field=InputFileSerializer)
    def get_location_file(self, instance):
        request = self.context.get('request')
        return _serialize_input_file(
            instance.location_file,
            instance.get_absolute_location_file_url(request=request),
            request,
        )

    @swagger_serializer_method(serializer_or_field=InputFileSerializer)
    def get_accounts_file(self, instance):
        request = self.context.get('request')
        return _serialize_input_file(
            instance.accounts_file,
            instance.get_absolute_accounts_file_url(request=request),
            request,
        )

    @swagger_serializer_method(serializer_or_field=InputFileSerializer)
    def get_reinsurance_info_file(self, instance):
        request = self.context.get('request')
        return _serialize_input_file(
            instance.reinsurance_info_file,
            instance.get_absolute_reinsurance_info_file_url(request=request),
            request,
        )

    @swagger_serializer_method(serializer_or_field=InputFileSerializer)
    def get_reinsurance_scope_file(self, instance):
        request = self.context.get('request')
        return _serialize_input_file(
            instance.reinsurance_scope_file,
            instance.get_absolute_reinsurance_scope_file_url(request=request),
            request,
        )


class PortfolioSerializer(serializers.ModelSerializer):
    accounts_file = serializers.SerializerMethodField()
    location_file = serializers.SerializerMethodField()
    reinsurance_info_file = serializers.SerializerMethodField()
    reinsurance_scope_file = serializers.SerializerMethodField()
    storage_links = serializers.SerializerMethodField()
    groups = serializers.SlugRelatedField(many=True, read_only=False, slug_field='name', required=False, queryset=Group.objects.all())

    class Meta:
        model = Portfolio
        fields = (
            'id',
            'name',
            'created',
            'modified',
            'groups',
            'location_file',
            'accounts_file',
            'reinsurance_info_file',
            'reinsurance_scope_file',
            'storage_links',
        )

    def validate(self, attrs):

        # Validate and update groups parameter
        validate_and_update_groups(self.partial, self.context.get('request').user, attrs)

        return super(serializers.ModelSerializer, self).validate(attrs)

    def create(self, validated_data):
        data = dict(validated_data)
        if not data.get('creator') and 'request' in self.context:
            data['creator'] = self.context.get('request').user
        return super(PortfolioSerializer, self).create(data)

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_storage_links(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_storage_url(request=request, namespace="v2-portfolios")

    def get_groups(self, instance):
        groups = []
        for group in instance.groups.all():
            groups.append(group.name)
        return groups

    @swagger_serializer_method(serializer_or_field=InputFileSerializer)
    def get_location_file(self, instance):
        request = self.context.get('request')
        return _serialize_input_file(
            instance.location_file,
            instance.get_absolute_location_file_url(request=request),
            request,
        )

    @swagger_serializer_method(serializer_or_field=InputFileSerializer)
    def get_accounts_file(self, instance):
        request = self.context.get('request')
        return _serialize_input_file(
            instance.accounts_file,
            instance.get_absolute_accounts_file_url(request=request),
            request,
        )

    @swagger_serializer_method(serializer_or_field=InputFileSerializer)
    def get_reinsurance_info_file(self, instance):
        request = self.context.get('request')
        return _serialize_input_file(
            instance.reinsurance_info_file,
            instance.get_absolute_reinsurance_info_file_url(request=request),
            request,
        )

    @swagger_serializer_method(serializer_or_field=InputFileSerializer)
    def get_reinsurance_scope_file(self, instance):
        request = self.context.get('request')
        return _serialize_input_file(
            instance.reinsurance_scope_file,
            instance.get_absolute_reinsurance_scope_file_url(request=request),
            request,
        )


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
        # Check AWS storage
        if hasattr(default_storage, 'bucket'):
            try:
                default_storage.bucket.Object(value).load()
                return True
            except S3_ClientError as e:
                if e.response['Error']['Code'] == "404":
                    return False
                else:
                    raise e
        # Check Azure Blob storage
        elif hasattr(default_storage, 'azure_container'):
            try:
                blob = default_storage.client.get_blob_client(value)
                blob.get_blob_properties()
                return True
            except Blob_ResourceNotFoundError:
                return False
        else:
            return default_storage.exists(value)

    def user_belongs_to_file_group(self, value):
        file = RelatedFile.objects.filter(file=value)
        if file:
            return validate_user_is_owner(self.context['request'].user, file[0])
        return True

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
                # Check String is not empty
                elif len(value.strip()) < 1:
                    errors[k] = "Value is empty or whitespace string."
                    continue
                # Check that the file exists
                elif not self.is_in_storage(value):
                    errors[k] = "File '{}' not found in default storage".format(value)
                    continue
                elif not self.user_belongs_to_file_group(value):
                    errors[k] = "File '{}' belongs to a different group".format(value)
                    continue

                # Data is valid
                attrs[k] = value
        if errors:
            raise serializers.ValidationError(errors)
        return super(PortfolioStorageSerializer, self).validate(attrs)

    def inferr_content_type(self, stored_filename):
        inferred_type = mimetypes.MimeTypes().guess_type(stored_filename)[0]
        if not inferred_type and stored_filename.lower().endswith('parquet'):
            # mimetypes dosn't work for parquet so handle that here
            inferred_type = 'application/octet-stream'
        if not inferred_type:
            inferred_type = default_storage.default_content_type
        return inferred_type

    def get_content_type(self, stored_filename):
        try:  # fetch content_type stored in Django's DB
            return RelatedFile.objects.get(file=path.basename(stored_filename)).content_type
        except ObjectDoesNotExist:
            # Find content_type from S3 Object header
            if hasattr(default_storage, 'bucket'):
                try:
                    object_header = default_storage.connection.meta.client.head_object(
                        Bucket=default_storage.bucket_name,
                        Key=stored_filename)
                    return object_header['ContentType']
                except S3_ClientError:
                    return self.inferr_content_type(stored_filename)

            #  Find content_type from Blob Storage
            elif hasattr(default_storage, 'azure_container'):
                blob_client = default_storage.client.get_blob_client(stored_filename)
                blob_properties = blob_client.get_blob_properties()
                return blob_properties.content_settings.content_type

            else:
                return self.inferr_content_type(stored_filename)

    def update(self, instance, validated_data):
        files_for_removal = list()
        user = self.context['request'].user
        for field in validated_data:
            old_file_name = validated_data[field]
            content_type = self.get_content_type(old_file_name)
            fname = path.basename(old_file_name)
            new_file_name = default_storage.get_alternative_name(fname, '')

            # S3 storage - File copy needed
            if hasattr(default_storage, 'bucket'):
                new_file = ContentFile(b'')
                new_file.name = new_file_name
                new_related_file = RelatedFile.objects.create(
                    file=new_file,
                    filename=fname,
                    content_type=content_type,
                    creator=user,
                    store_as_filename=True,
                )
                new_related_file.groups.set(user.groups.all())
                new_related_file.save()
                bucket = default_storage.bucket
                stored_file = default_storage.open(new_related_file.file.name)
                stored_file.obj.copy({"Bucket": bucket.name, "Key": validated_data[field]})
                stored_file.obj.wait_until_exists()

            elif hasattr(default_storage, 'azure_container'):
                # https://docs.microsoft.com/en-us/azure/storage/blobs/storage-blob-copy?tabs=python
                new_file_name = default_storage.get_alternative_name(old_file_name, '')
                new_blobname = '/'.join([default_storage.location, path.basename(new_file_name)])

                # Copies a blob asynchronously.
                source_blob = default_storage.client.get_blob_client(old_file_name)
                dest_blob = default_storage.client.get_blob_client(new_blobname)

                try:
                    lease = BlobLeaseClient(source_blob)
                    lease.acquire()
                    dest_blob.start_copy_from_url(source_blob.url)
                    wait_for_blob_copy(dest_blob)
                    lease.break_lease()
                except Exception as e:
                    # copy failed, break file lease and re-raise
                    lease.break_lease()
                    raise e

                stored_blob = default_storage.open(new_file_name)
                new_related_file = RelatedFile.objects.create(
                    file=File(stored_blob, name=new_file_name),
                    filename=fname,
                    content_type=content_type,
                    creator=user,
                    store_as_filename=True,
                )

            # Shared-fs
            else:
                stored_file = default_storage.open(old_file_name)
                new_file = File(stored_file, name=new_file_name)
                new_related_file = RelatedFile.objects.create(
                    file=new_file,
                    filename=fname,
                    content_type=content_type,
                    creator=user,
                    store_as_filename=True,
                )
                new_related_file.groups.set(user.groups.all())
                new_related_file.save()

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
        fields = ['name', 'model', 'groups']

    def __init__(self, portfolio=None, *args, **kwargs):
        self.portfolio = portfolio
        super(CreateAnalysisSerializer, self).__init__(*args, **kwargs)

    def validate(self, attrs):
        attrs['portfolio'] = self.portfolio
        if not self.portfolio.location_file:
            raise ValidationError({'portfolio': '"location_file" must not be null'})

        # Validate and update groups parameter
        validate_and_update_groups(self.partial, self.context.get('request').user, attrs)

        return attrs

    def create(self, validated_data):
        data = dict(validated_data)
        if 'request' in self.context:
            data['creator'] = self.context.get('request').user
        return super(CreateAnalysisSerializer, self).create(data)


class PortfolioValidationSerializer(serializers.ModelSerializer):
    accounts_validated = serializers.SerializerMethodField()
    location_validated = serializers.SerializerMethodField()
    reinsurance_info_validated = serializers.SerializerMethodField()
    reinsurance_scope_validated = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = (
            'location_validated',
            'accounts_validated',
            'reinsurance_info_validated',
            'reinsurance_scope_validated',
        )

    @swagger_serializer_method(serializer_or_field=serializers.CharField)  # should it be BooleanField ?
    def get_location_validated(self, instance):
        if instance.location_file:
            return instance.location_file.oed_validated

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_accounts_validated(self, instance):
        if instance.accounts_file:
            return instance.accounts_file.oed_validated

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_reinsurance_info_validated(self, instance):
        if instance.reinsurance_info_file:
            return instance.reinsurance_info_file.oed_validated

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_reinsurance_scope_validated(self, instance):
        if instance.reinsurance_scope_file:
            return instance.reinsurance_scope_file.oed_validated
