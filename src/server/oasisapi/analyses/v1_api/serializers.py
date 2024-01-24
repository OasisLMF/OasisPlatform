from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..models import Analysis
from ...files.models import file_storage_link


class AnalysisListSerializer(serializers.Serializer):
    """ Read Only Analyses Deserializer for efficiently returning a list of all
        Analyses from DB
    """

    # model fields
    created = serializers.DateTimeField(read_only=True)
    modified = serializers.DateTimeField(read_only=True)
    name = serializers.CharField(read_only=True)
    id = serializers.IntegerField(read_only=True)
    portfolio = serializers.IntegerField(source='portfolio_id', read_only=True)
    model = serializers.IntegerField(source='model_id', read_only=True)
    status = serializers.CharField(read_only=True)
    task_started = serializers.DateTimeField(read_only=True)
    task_finished = serializers.DateTimeField(read_only=True)
    complex_model_data_files = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    # file fields
    input_file = serializers.SerializerMethodField(read_only=True)
    settings_file = serializers.SerializerMethodField(read_only=True)
    settings = serializers.SerializerMethodField(read_only=True)
    lookup_errors_file = serializers.SerializerMethodField(read_only=True)
    lookup_success_file = serializers.SerializerMethodField(read_only=True)
    lookup_validation_file = serializers.SerializerMethodField(read_only=True)
    summary_levels_file = serializers.SerializerMethodField(read_only=True)
    input_generation_traceback_file = serializers.SerializerMethodField(read_only=True)
    output_file = serializers.SerializerMethodField(read_only=True)
    run_traceback_file = serializers.SerializerMethodField(read_only=True)
    run_log_file = serializers.SerializerMethodField(read_only=True)
    storage_links = serializers.SerializerMethodField(read_only=True)

    class Meta:
        ref_name = "v1_" + __qualname__.split('.')[0]

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_input_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_input_file_url(request=request) if instance.input_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_settings_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_settings_file_url(request=request) if instance.settings_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_settings(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_settings_url(request=request) if instance.settings_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_lookup_errors_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_lookup_errors_file_url(request=request) if instance.lookup_errors_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_lookup_success_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_lookup_success_file_url(request=request) if instance.lookup_success_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_lookup_validation_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_lookup_validation_file_url(request=request) if instance.lookup_validation_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_summary_levels_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_summary_levels_file_url(request=request) if instance.summary_levels_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_input_generation_traceback_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_input_generation_traceback_file_url(request=request) if instance.input_generation_traceback_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_output_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_output_file_url(request=request) if instance.output_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_run_traceback_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_run_traceback_file_url(request=request) if instance.run_traceback_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_run_log_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_run_log_file_url(request=request) if instance.run_log_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_storage_links(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_storage_url(request=request)


class AnalysisSerializer(serializers.ModelSerializer):
    input_file = serializers.SerializerMethodField()
    settings_file = serializers.SerializerMethodField()
    settings = serializers.SerializerMethodField()
    lookup_errors_file = serializers.SerializerMethodField()
    lookup_success_file = serializers.SerializerMethodField()
    lookup_validation_file = serializers.SerializerMethodField()
    summary_levels_file = serializers.SerializerMethodField()
    input_generation_traceback_file = serializers.SerializerMethodField()
    output_file = serializers.SerializerMethodField()
    run_traceback_file = serializers.SerializerMethodField()
    run_log_file = serializers.SerializerMethodField()
    storage_links = serializers.SerializerMethodField()
    ns = 'v1-analyses'

    class Meta:
        ref_name = "v1_" + __qualname__.split('.')[0]
        model = Analysis
        fields = (
            'created',
            'modified',
            'name',
            'id',
            'portfolio',
            'model',
            'status',
            'task_started',
            'task_finished',
            'complex_model_data_files',
            'input_file',
            'settings_file',
            'settings',
            'lookup_errors_file',
            'lookup_success_file',
            'lookup_validation_file',
            'summary_levels_file',
            'input_generation_traceback_file',
            'output_file',
            'run_traceback_file',
            'run_log_file',
            'storage_links',
        )

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_input_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_input_file_url(request=request, namespace=self.ns) if instance.input_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_settings_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_settings_file_url(request=request, namespace=self.ns) if instance.settings_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_settings(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_settings_url(request=request, namespace=self.ns) if instance.settings_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_lookup_errors_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_lookup_errors_file_url(request=request, namespace=self.ns) if instance.lookup_errors_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_lookup_success_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_lookup_success_file_url(request=request, namespace=self.ns) if instance.lookup_success_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_lookup_validation_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_lookup_validation_file_url(request=request, namespace=self.ns) if instance.lookup_validation_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_summary_levels_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_summary_levels_file_url(request=request, namespace=self.ns) if instance.summary_levels_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_input_generation_traceback_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_input_generation_traceback_file_url(request=request, namespace=self.ns) if instance.input_generation_traceback_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_output_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_output_file_url(request=request, namespace=self.ns) if instance.output_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_run_traceback_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_run_traceback_file_url(request=request, namespace=self.ns) if instance.run_traceback_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_run_log_file(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_run_log_file_url(request=request, namespace=self.ns) if instance.run_log_file_id else None

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_storage_links(self, instance):
        request = self.context.get('request')
        return instance.get_absolute_storage_url(request=request, namespace=self.ns)

    def validate(self, attrs):
        if not attrs.get('creator') and 'request' in self.context:
            attrs['creator'] = self.context.get('request').user

        # Check that portfilio has a location file
        if attrs.get('portfolio'):
            if not attrs['portfolio'].location_file:
                raise ValidationError({'portfolio': '"location_file" must not be null'})

        # check that model isn't soft-deleted
        if attrs.get('model'):
            if attrs['model'].deleted:
                raise ValidationError({'model': ["Model pk '{}' - has been deleted.".format(attrs['model'].id)]})
            if attrs['model'].run_mode != attrs['model'].run_mode_choices.V1:
                raise ValidationError({
                    'model': ["Model pk '{}' - Unsuppored Operation, 'run_mode' must be 'V1', not '{}'".format(
                        attrs['model'].id,
                        attrs['model'].run_mode,
                    )]
                })

        return attrs


class AnalysisStorageSerializer(serializers.ModelSerializer):
    settings_file = serializers.SerializerMethodField()
    input_file = serializers.SerializerMethodField()
    input_generation_traceback_file = serializers.SerializerMethodField()
    output_file = serializers.SerializerMethodField()
    run_traceback_file = serializers.SerializerMethodField()
    run_log_file = serializers.SerializerMethodField()
    lookup_errors_file = serializers.SerializerMethodField()
    lookup_success_file = serializers.SerializerMethodField()
    lookup_validation_file = serializers.SerializerMethodField()
    summary_levels_file = serializers.SerializerMethodField()

    class Meta:
        ref_name = "v1_" + __qualname__.split('.')[0]
        model = Analysis
        fields = (
            'settings_file',
            'input_file',
            'input_generation_traceback_file',
            'output_file',
            'run_traceback_file',
            'run_log_file',
            'lookup_errors_file',
            'lookup_success_file',
            'lookup_validation_file',
            'summary_levels_file',
        )

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_settings_file(self, instance):
        return file_storage_link(instance.settings_file, True)

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_input_file(self, instance):
        return file_storage_link(instance.input_file, True)

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_input_generation_traceback_file(self, instance):
        return file_storage_link(instance.input_generation_traceback_file, True)

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_output_file(self, instance):
        return file_storage_link(instance.output_file, True)

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_run_traceback_file(self, instance):
        return file_storage_link(instance.run_traceback_file, True)

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_run_log_file(self, instance):
        return file_storage_link(instance.run_log_file, True)

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_lookup_errors_file(self, instance):
        return file_storage_link(instance.lookup_errors_file, True)

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_lookup_success_file(self, instance):
        return file_storage_link(instance.lookup_success_file, True)

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_lookup_validation_file(self, instance):
        return file_storage_link(instance.lookup_validation_file, True)

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_summary_levels_file(self, instance):
        return file_storage_link(instance.summary_levels_file, True)


class AnalysisCopySerializer(AnalysisSerializer):

    def __init__(self, *args, **kwargs):
        super(AnalysisCopySerializer, self).__init__(*args, **kwargs)

        self.fields['portfolio'].required = False
        self.fields['model'].required = False
        self.fields['name'].required = False
