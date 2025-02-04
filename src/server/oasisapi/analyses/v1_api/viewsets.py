from __future__ import absolute_import

from django.utils.translation import gettext_lazy as _
from django.utils.decorators import method_decorator
from django.conf import settings

from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.serializers import Serializer
from rest_framework.exceptions import APIException

from drf_yasg.utils import swagger_auto_schema
from django_filters import rest_framework as filters
from django_filters import NumberFilter

from ..models import Analysis
from .serializers import AnalysisSerializer, AnalysisCopySerializer, AnalysisStorageSerializer, AnalysisListSerializer

from ...analysis_models.models import AnalysisModel
from ...data_files.v1_api.serializers import DataFileSerializer
from ...filters import TimeStampedFilter, CsvMultipleChoiceFilter, CsvModelMultipleChoiceFilter
from ...files.v1_api.views import handle_related_file, handle_json_data
from ...files.v1_api.serializers import RelatedFileSerializer
from ...schemas.custom_swagger import FILE_RESPONSE
from ...schemas.serializers import AnalysisSettingsSerializer


class LogAcessDenied(APIException):
    status_code = 403
    default_detail = 'Only accounts with staff access are alowed to view system logs.'
    default_code = 'system logs disabled by admin'


class check_log_permission(permissions.BasePermission):
    RESTRICTED_ACTIONS = [
        'input_generation_traceback_file',
        'run_traceback_file',
        'run_log_file'
    ]

    def has_permission(self, request, view):
        if not settings.RESTRICT_SYSTEM_LOGS:  # are analyses log restricted?
            return True
        if request.user.is_staff:  # user is admin?
            return True
        # was it a system log message?
        if view.action not in self.RESTRICTED_ACTIONS:  # request for a log file?
            return True
        else:
            raise LogAcessDenied


class AnalysisFilter(TimeStampedFilter):
    name = filters.CharFilter(
        help_text=_('Filter results by case insensitive names equal to the given string'),
        lookup_expr='iexact'
    )
    name__contains = filters.CharFilter(
        help_text=_('Filter results by case insensitive name containing the given string'),
        lookup_expr='icontains',
        field_name='name'
    )
    status = filters.ChoiceFilter(
        help_text=_('Filter results by results in the current analysis status, one of [{}]'.format(
            ', '.join(Analysis.status_choices._db_values))
        ),
        choices=Analysis.status_choices,
    )
    status__in = CsvMultipleChoiceFilter(
        help_text=_(
            'Filter results by results where the current analysis status '
            'is one of a given set (provide multiple parameters or comma separated list), '
            'from [{}]'.format(', '.join(Analysis.status_choices._db_values))
        ),
        choices=Analysis.status_choices,
        field_name='status',
        label=_('Status in')
    )
    model = NumberFilter(
        help_text=_('Filter results by the id of the model the analysis belongs to'),
        field_name='model'
    )
    model__in = CsvModelMultipleChoiceFilter(
        help_text=_('Filter results by the id of the model the analysis belongs to'),
        field_name='model',
        label=_('Model in'),
        queryset=AnalysisModel.objects.all(),
    )
    user = filters.CharFilter(
        help_text=_('Filter results by case insensitive `user` equal to the given string'),
        lookup_expr='iexact',
        field_name='creator__username'
    )

    class Meta:
        model = Analysis
        fields = [
            'name',
            'name__contains',
            'status',
            'status__in',
            'model',
            'model__in',
            'user',
        ]

    def __init__(self, *args, **kwargs):
        super(AnalysisFilter, self).__init__(*args, **kwargs)


@method_decorator(name='list', decorator=swagger_auto_schema(responses={200: AnalysisSerializer(many=True)}))
class AnalysisViewSet(viewsets.ModelViewSet):
    """
    list:
    Returns a list of Analysis objects.

    ### Examples

    To get all analyses with 'foo' in their name

        /analyses/?name__contains=foo

    To get all analyses created on 1970-01-01

        /analyses/?created__date=1970-01-01

    To get all analyses updated before 2000-01-01

        /analyses/?modified__lt=2000-01-01

    To get all analyses in the `NEW` state

        /analyses/?status=NEW

    To get all started and pending tasks

        /analyses/?status__in=PENDING&status__in=STARTED

    To get all models in model `1`

        /analyses/?model=1

    To get all models in models `2` and `3`

        /analyses/?model__in=2&model__in=3

    retrieve:
    Returns the specific analysis entry.

    create:
    Creates a analysis based on the input data

    update:
    Updates the specified analysis

    partial_update:
    Partially updates the specified analysis (only provided fields are updated)
    """
    file_action_types = ['settings_file',
                         'input_file',
                         'lookup_errors_file',
                         'lookup_success_file',
                         'lookup_validation_file',
                         'summary_levels_file',
                         'input_generation_traceback_file',
                         'run_traceback_file',
                         'output_file',
                         'run_traceback_file']

    task_action_types = ['run',
                         'cancel',
                         'generate_inputs',
                         'cancel_generate_inputs']

    queryset = Analysis.objects.all().select_related(*file_action_types).prefetch_related('complex_model_data_files')
    serializer_class = AnalysisSerializer
    filterset_class = AnalysisFilter
    permission_classes = (permissions.IsAuthenticated, check_log_permission)

    file_action_types.append('set_settings_file')

    def get_serializer_class(self):
        if self.action in ['create', 'options', 'update', 'partial_update', 'retrieve']:
            return super().get_serializer_class()
        elif self.action in ['list']:
            return AnalysisListSerializer
        elif self.action == 'copy':
            return AnalysisCopySerializer
        elif self.action == 'data_files':
            return DataFileSerializer
        elif self.action == 'storage_links':
            return AnalysisStorageSerializer
        elif self.action in self.file_action_types:
            return RelatedFileSerializer
        else:
            return Serializer

    @property
    def parser_classes(self):
        if getattr(self, 'action', None) in ['set_settings_file']:
            return [MultiPartParser]
        else:
            return api_settings.DEFAULT_PARSER_CLASSES

    @swagger_auto_schema(responses={200: AnalysisSerializer})
    @action(methods=['post'], detail=True)
    def run(self, request, pk=None, version=None):
        """
        Runs all the analysis. The analysis must have one of the following
        statuses, `NEW`, `RUN_COMPLETED`, `RUN_CANCELLED` or
        `RUN_ERROR`
        """
        obj = self.get_object()
        if obj.model.run_mode != obj.model.run_mode_choices.V1:
            obj.raise_validate_errors(
                {'model': [f"Model pk {obj.model.id}' - Unsupported Operation, 'run_mode' must be 'V1', not '{obj.model.run_mode}'"]}
            )
        else:
            obj.run(request.user)
            return Response(AnalysisSerializer(instance=obj, context=self.get_serializer_context()).data)

    @swagger_auto_schema(responses={200: AnalysisSerializer})
    @action(methods=['post'], detail=True)
    def cancel(self, request, pk=None, version=None):
        """
        Cancels either input generation or analysis execution depending on the active stage.
        The analysis must have one of the following statuses, `INPUTS_GENERATION_QUEUED`, `INPUTS_GENERATION_STARTED`, `RUN_QUEUED` or `RUN_STARTED`
        """
        obj = self.get_object()
        obj.cancel_any()
        return Response(AnalysisSerializer(instance=obj, context=self.get_serializer_context()).data)

    @swagger_auto_schema(responses={200: AnalysisSerializer})
    @action(methods=['post'], detail=True)
    def cancel_analysis_run(self, request, pk=None, version=None):
        """
        Cancels a running analysis execution. The analysis must have one of the following statuses, `RUN_QUEUED` or `RUN_STARTED`
        """
        obj = self.get_object()
        obj.cancel_analysis()
        return Response(AnalysisSerializer(instance=obj, context=self.get_serializer_context()).data)

    @swagger_auto_schema(responses={200: AnalysisSerializer})
    @action(methods=['post'], detail=True)
    def generate_inputs(self, request, pk=None, version=None):
        """
        Generates the inputs for the analysis based on the portfolio.
        The analysis must have one of the following statuses, `INPUTS_GENERATION_QUEUED` or `INPUTS_GENERATION_STARTED`
        """
        obj = self.get_object()
        # Check run_mode == V1 before dispatch
        if obj.model.run_mode != obj.model.run_mode_choices.V1:
            obj.raise_validate_errors(
                {'model': [f"Model pk {obj.model.id}' - Unsupported Operation, 'run_mode' must be 'V1', not '{obj.model.run_mode}'"]}
            )
        else:
            obj.generate_inputs(request.user)
            return Response(AnalysisSerializer(instance=obj, context=self.get_serializer_context()).data)

    @swagger_auto_schema(responses={200: AnalysisSerializer})
    @action(methods=['post'], detail=True)
    def cancel_generate_inputs(self, request, pk=None, version=None):
        """
        Cancels a currently inputs generation. The analysis status must be `INPUTS_GENERATION_STARTED`
        """
        obj = self.get_object()
        obj.cancel_generate_inputs()
        return Response(AnalysisSerializer(instance=obj, context=self.get_serializer_context()).data)

    @action(methods=['post'], detail=True)
    def copy(self, request, pk=None, version=None):
        """
        Copies an existing analysis, copying the associated input files and model and modifying
        it's name (if none is provided) and resets the status, input errors and outputs
        """
        obj = self.get_object()
        new_obj = obj.copy()

        new_obj.save()
        new_obj.creator = None

        serializer = self.get_serializer(instance=new_obj, data=request.data, context=self.get_serializer_context(), partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    @swagger_auto_schema(methods=['get'], responses={200: FILE_RESPONSE})
    @action(methods=['get', 'delete'], detail=True)
    def settings_file(self, request, pk=None, version=None):
        """
        get:
        Gets the portfolios `settings_file` contents

        delete:
        Disassociates the portfolios `settings_file` contents
        """
        return handle_related_file(self.get_object(), 'settings_file', request, ['application/json'])

    @settings_file.mapping.post
    def set_settings_file(self, request, pk=None, version=None):
        """
        post:
        Sets the portfolios `settings_file` contents
        """
        return handle_related_file(self.get_object(), 'settings_file', request, ['application/json'])

    @swagger_auto_schema(methods=['get'], responses={200: FILE_RESPONSE})
    @action(methods=['get'], detail=True)
    def input_file(self, request, pk=None, version=None):
        """
        get:
        Gets the portfolios `input_file` contents

        delete:
        Disassociates the portfolios `input_file` contents
        """
        return handle_related_file(self.get_object(), 'input_file', request, ['application/x-gzip', 'application/gzip', 'application/x-tar', 'application/tar'])

    @swagger_auto_schema(methods=['get'], responses={200: FILE_RESPONSE})
    @action(methods=['get'], detail=True)
    def lookup_errors_file(self, request, pk=None, version=None):
        """
        get:
        Gets the portfolios `lookup_errors_file` contents

        post:
        Sets the portfolios `lookup_errors_file` contents

        delete:
        Disassociates the portfolios `lookup_errors_file` contents
        """
        return handle_related_file(self.get_object(), 'lookup_errors_file', request, ['text/csv'])

    @swagger_auto_schema(methods=['get'], responses={200: FILE_RESPONSE})
    @action(methods=['get'], detail=True)
    def lookup_success_file(self, request, pk=None, version=None):
        """
        get:
        Gets the portfolios `lookup_success_file` contents

        post:
        Sets the portfolios `lookup_success_file` contents

        delete:
        Disassociates the portfolios `lookup_success_file` contents
        """
        return handle_related_file(self.get_object(), 'lookup_success_file', request, ['text/csv'])

    @swagger_auto_schema(methods=['get'], responses={200: FILE_RESPONSE})
    @action(methods=['get'], detail=True)
    def lookup_validation_file(self, request, pk=None, version=None):
        """
        get:
        Gets the portfolios `lookup_validation_file` contents

        post:
        Sets the portfolios `lookup_validation_file` contents

        delete:
        Disassociates the portfolios `lookup_validation_file` contents
        """
        return handle_related_file(self.get_object(), 'lookup_validation_file', request, ['application/json'])

    @swagger_auto_schema(methods=['get'], responses={200: FILE_RESPONSE})
    @action(methods=['get'], detail=True)
    def summary_levels_file(self, request, pk=None, version=None):
        """
        get:
        Gets the portfolios `summary_levels_file` contents

        post:
        Sets the portfolios `summary_levels_file` contents

        delete:
        Disassociates the portfolios `summary_levels_file` contents
        """
        return handle_related_file(self.get_object(), 'summary_levels_file', request, ['application/json'])

    @swagger_auto_schema(methods=['get'], responses={200: FILE_RESPONSE})
    @action(methods=['get', 'delete'], detail=True)
    def input_generation_traceback_file(self, request, pk=None, version=None):
        """
        get:
        Gets the portfolios `input_generation_traceback_file` contents

        delete:
        Disassociates the portfolios `input_generation_traceback_file` contents
        """
        return handle_related_file(self.get_object(), 'input_generation_traceback_file', request, ['text/plain'])

    @swagger_auto_schema(methods=['get'], responses={200: FILE_RESPONSE})
    @action(methods=['get', 'delete'], detail=True)
    def output_file(self, request, pk=None, version=None):
        """
        get:
        Gets the portfolios `output_file` contents

        delete:
        Disassociates the portfolios `output_file` contents
        """
        return handle_related_file(self.get_object(), 'output_file', request, ['application/x-gzip', 'application/gzip', 'application/x-tar', 'application/tar'])

    @swagger_auto_schema(methods=['get'], responses={200: FILE_RESPONSE})
    @action(methods=['get', 'delete'], detail=True)
    def run_traceback_file(self, request, pk=None, version=None):
        """
        get:
        Gets the portfolios `run_traceback_file` contents

        delete:
        Disassociates the portfolios `run_traceback_file` contents
        """
        return handle_related_file(self.get_object(), 'run_traceback_file', request, ['text/plain'])

    @swagger_auto_schema(methods=['get'], responses={200: FILE_RESPONSE})
    @action(methods=['get', 'delete'], detail=True)
    def run_log_file(self, request, pk=None, version=None):
        """
        get:
        Gets the portfolios `run_log_file` contents

        delete:
        Disassociates the portfolios `run_log_file` contents
        """
        return handle_related_file(self.get_object(), 'run_log_file', request, ['text/plain'])

    @swagger_auto_schema(responses={200: DataFileSerializer(many=True)})
    @action(methods=['get'], detail=True)
    def data_files(self, request, pk=None, version=None):
        df = self.get_object().complex_model_data_files.all()
        context = {'request': request}

        df_serializer = DataFileSerializer(df, many=True, context=context)
        return Response(df_serializer.data)

    @action(methods=['get'], detail=True)
    def storage_links(self, request, pk=None, version=None):
        """
        get:
        Gets the analyses storage backed link references, `object keys` or `file paths`
        """
        serializer = self.get_serializer(self.get_object())
        return Response(serializer.data)


class AnalysisSettingsView(viewsets.ModelViewSet):
    """
    list:
    Return the settings of an Analysis object.
    """
    queryset = Analysis.objects.all()
    serializer_class = AnalysisSerializer
    filterset_class = AnalysisFilter

    @swagger_auto_schema(methods=['get'], responses={200: AnalysisSettingsSerializer})
    @swagger_auto_schema(methods=['post'], request_body=AnalysisSettingsSerializer, responses={201: RelatedFileSerializer})
    @action(methods=['get', 'post', 'delete'], detail=True)
    def analysis_settings(self, request, pk=None, version=None):
        """
        get:
        Gets the analyses `settings` contents

        post:
        Sets the analyses `settings` contents

        delete:
        Disassociates the portfolios `settings_file` contents
        """
        return handle_json_data(self.get_object(), 'settings_file', request, AnalysisSettingsSerializer)
