from rest_framework import serializers
from rest_framework.reverse import reverse

from .models import ExternalJob, ExternalProviderSettings


class BboxField(serializers.ListField):
    child = serializers.FloatField()

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if len(value) != 4:
            raise serializers.ValidationError(
                'bbox must have exactly 4 values: [min_lon, min_lat, max_lon, max_lat]'
            )
        min_lon, min_lat, max_lon, max_lat = value
        if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
            raise serializers.ValidationError('longitudes must be in [-180, 180]')
        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise serializers.ValidationError('latitudes must be in [-90, 90]')
        if min_lon > max_lon:
            raise serializers.ValidationError(
                'min_lon > max_lon; antimeridian-crossing bboxes are not supported — issue two separate requests'
            )
        if min_lat > max_lat:
            raise serializers.ValidationError('min_lat must be <= max_lat')
        return value


class FiltersSerializer(serializers.Serializer):
    peril = serializers.CharField(required=False)
    lob = serializers.ListField(child=serializers.CharField(), required=False)
    admin = serializers.CharField(required=False)
    bbox = BboxField(
        required=False,
        help_text='[min_lon, min_lat, max_lon, max_lat] in WGS84. '
                  'Antimeridian-crossing not supported; issue two requests.',
    )


class ExternalLocationFileRequestSerializer(serializers.Serializer):
    country_code = serializers.CharField(
        max_length=2, min_length=2,
        help_text='ISO 3166-1 alpha-2 country code, e.g. "GH"',
    )
    filters = FiltersSerializer(required=False)
    format = serializers.ChoiceField(choices=['csv', 'parquet'], default='csv')
    as_of = serializers.DateTimeField(
        required=False,
        help_text='Pin the GXM dataset snapshot to this UTC timestamp',
    )


class ExternalEnrichRequestSerializer(serializers.Serializer):
    fields = serializers.ListField(
        child=serializers.CharField(),
        help_text='OED field names to fill, e.g. ["OccupancyCode","ConstructionCode","NumberOfStoreys"]',
    )
    match_radius_m = serializers.FloatField(
        required=False, min_value=0,
        help_text='Maximum distance in metres to match a GXM building footprint',
    )
    overwrite = serializers.BooleanField(
        default=False,
        help_text='If false (default), user-supplied values are never overwritten',
    )
    format = serializers.ChoiceField(choices=['csv', 'parquet'], default='csv')


class ExternalJobAcceptedSerializer(serializers.Serializer):
    job_id = serializers.UUIDField()
    status = serializers.CharField()
    status_url = serializers.URLField()


class ExternalJobSerializer(serializers.ModelSerializer):
    status_url = serializers.SerializerMethodField()
    result_file_url = serializers.SerializerMethodField()
    audit_url = serializers.SerializerMethodField()

    class Meta:
        model = ExternalJob
        fields = (
            'id',
            'provider',
            'job_type',
            'portfolio',
            'status',
            'request_data',
            'error_message',
            'started',
            'finished',
            'created',
            'modified',
            'status_url',
            'result_file_url',
            'audit_url',
        )
        read_only_fields = fields

    def get_status_url(self, instance):
        request = self.context.get('request')
        return reverse(
            'v2-external-providers:external-job-detail',
            kwargs={
                'provider': instance.provider,
                'portfolio_pk': instance.portfolio_id,
                'job_id': str(instance.id),
            },
            request=request,
        )

    def get_result_file_url(self, instance):
        if not instance.result_file:
            return None
        request = self.context.get('request')
        return reverse(
            'v2-portfolios:portfolio-location-file',
            kwargs={'pk': instance.portfolio_id},
            request=request,
        )

    def get_audit_url(self, instance):
        if not instance.audit_file or not instance.audit_file.file:
            return None
        try:
            return instance.audit_file.file.url
        except Exception:
            return None


class ExternalProviderSettingsSerializer(serializers.ModelSerializer):
    client_secret = serializers.CharField(
        write_only=True, required=False,
        help_text='Write-only. Never returned in responses.',
    )

    class Meta:
        model = ExternalProviderSettings
        fields = (
            'provider',
            'base_url',
            'client_id',
            'client_secret',
            'default_as_of',
            'entitlements_cache',
            'updated',
        )
        read_only_fields = ('provider', 'updated')
