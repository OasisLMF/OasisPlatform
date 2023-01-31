from os import path

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

from .models import Portfolio
from ..analyses.serializers import AnalysisSerializer
from ..files.models import RelatedFile
from ..files.models import file_storage_link
from ..files.upload import wait_for_blob_copy
from ..permissions.group_auth import validate_and_update_groups, validate_user_is_owner
from ..schemas.serializers import (
    LocFileSerializer,
    AccFileSerializer,
    ReinsInfoFileSerializer,
    ReinsScopeFileSerializer,
)


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
        return instance.get_absolute_storage_url(request=request)

    @swagger_serializer_method(serializer_or_field=LocFileSerializer)
    def get_location_file(self, instance):
        if instance.location_file_id is None:
            return None
        request = self.context.get('request')
        return {
            "uri": instance.get_absolute_location_file_url(request=request),
            "name": instance.location_file.filename,
            "stored": str(instance.location_file.file)
        }

    @swagger_serializer_method(serializer_or_field=AccFileSerializer)
    def get_accounts_file(self, instance):
        if instance.accounts_file_id is None:
            return None
        request = self.context.get('request')
        return {
            "uri": instance.get_absolute_accounts_file_url(request=request),
            "name": instance.accounts_file.filename,
            "stored": str(instance.accounts_file.file)
        }

    @swagger_serializer_method(serializer_or_field=ReinsInfoFileSerializer)
    def get_reinsurance_info_file(self, instance):
        if instance.reinsurance_info_file_id is None:
            return None

        request = self.context.get('request')
        return {
            "uri": instance.get_absolute_reinsurance_info_file_url(request=request),
            "name": instance.reinsurance_info_file.filename,
            "stored": str(instance.reinsurance_info_file.file)
        }

    @swagger_serializer_method(serializer_or_field=ReinsScopeFileSerializer)
    def get_reinsurance_scope_file(self, instance):
        if instance.reinsurance_scope_file_id is None:
            return None
        request = self.context.get('request')
        return {
            "uri": instance.get_absolute_reinsurance_scope_file_url(request=request),
            "name": instance.reinsurance_scope_file.filename,
            "stored": str(instance.reinsurance_scope_file.file)
        }


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
        return instance.get_absolute_storage_url(request=request)

    def get_groups(self, instance):
        groups = []
        for group in instance.groups.all():
            groups.append(group.name)
        return groups

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

    def get_content_type(self, stored_filename):
        try:  # fetch content_type stored in Django's DB
            return RelatedFile.objects.get(file=path.basename(stored_filename)).content_type
        except ObjectDoesNotExist:
            try:  # Find content_type from S3 Object header
                object_header = default_storage.connection.meta.client.head_object(
                    Bucket=default_storage.bucket_name,
                    Key=stored_filename)
                return object_header['ContentType']
            except ClientError:
                # fallback to the default content_type
                return default_storage.default_content_type

    def update(self, instance, validated_data):
        files_for_removal = list()
        user = self.context['request'].user
        for field in validated_data:
            content_type = self.get_content_type(validated_data[field])

            # S3 storage - File copy needed
            if hasattr(default_storage, 'bucket'):
                fname = path.basename(validated_data[field])
                new_file = ContentFile(b'')
                new_file.name = default_storage.get_alternative_name(fname, '')
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
                fname = path.basename(validated_data[field])
                new_file_name = default_storage.get_alternative_name(validated_data[field], '')
                new_blobname = path.basename(new_file_name)

                # Copies a blob asynchronously.
                source_blob = default_storage.client.get_blob_client(validated_data[field])
                dest_blob = default_storage.client.get_blob_client(new_file_name)

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

                stored_blob = default_storage.open(new_blobname)
                new_related_file = RelatedFile.objects.create(
                    file=File(stored_blob, name=new_blobname),
                    filename=fname,
                    content_type=content_type,
                    creator=self.context['request'].user,
                    store_as_filename=True,
                )

            # Shared-fs
            else:
                stored_file = default_storage.open(validated_data[field])
                new_file = File(stored_file, name=validated_data[field])
                new_related_file = RelatedFile.objects.create(
                    file=new_file,
                    filename=validated_data[field],
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
