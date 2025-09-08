from __future__ import absolute_import

from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from django.conf import settings as django_settings
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.status import HTTP_201_CREATED
from ..models import Portfolio
# from ...decorators import requires_sql_reader -- LOT3
from ...schemas.serializers import StorageLinkSerializer
from .serializers import (
    PortfolioSerializer,
    CreateAnalysisSerializer,
    PortfolioStorageSerializer,
    PortfolioListSerializer,
    PortfolioValidationSerializer,
    ExposureRunSerializer,
    ExposureTransformSerializer
)

from ...analyses.v2_api.serializers import AnalysisSerializer
from ...files.v2_api.serializers import RelatedFileSerializer, FileSQLSerializer
from ...files.v2_api.views import handle_related_file
# from ...files.v2_api.views import handle_related_file_sql -- LOT3
from ...filters import TimeStampedFilter
from ...permissions.group_auth import VerifyGroupAccessModelViewSet
from ...schemas.custom_swagger import FILE_HEADERS, FILE_RESPONSE, FILE_FORMAT_PARAM, FILE_VALIDATION_PARAM
from ...files.models import RelatedFile


class PortfolioFilter(TimeStampedFilter):
    name = filters.CharFilter(help_text=_('Filter results by case insensitive names equal to the given string'), lookup_expr='iexact')
    name__contains = filters.CharFilter(help_text=_(
        'Filter results by case insensitive name containing the given string'), lookup_expr='icontains', field_name='name')
    user = filters.CharFilter(
        help_text=_('Filter results by case insensitive `user` equal to the given string'),
        lookup_expr='iexact',
        field_name='creator__username'
    )

    class Meta:
        model = Portfolio
        fields = [
            'name',
            'name__contains',
            'user',
        ]


@extend_schema_view(list=extend_schema(responses={200: PortfolioSerializer(many=True)}))
class PortfolioViewSet(VerifyGroupAccessModelViewSet):
    """
    list:
    Returns a list of Portfolio objects.

    ### Examples

    To get all portfolios with 'foo' in their name

        /portfolio/?name__contains=foo

    To get all portfolios created on 1970-01-01

        /portfolio/?created__date=1970-01-01

    To get all portfolios updated before 2000-01-01

        /portfolio/?modified__lt=2000-01-01

    retrieve:
    Returns the specific portfolio entry.

    create:
    Creates a portfolio based on the input data

    update:
    Updates the specified portfolio

    partial_update:
    Partially updates the specified portfolio (only provided fields are updated)
    """

    serializer_class = PortfolioSerializer
    filterset_class = PortfolioFilter

    supported_mime_types = [
        'application/octet-stream',
        'application/json',
        'text/csv',
        'application/gzip',
        'application/zip',
        'application/x-bzip2',
    ]

    group_access_model = Portfolio

    def get_queryset(self):

        return super().get_queryset().select_related(
            'location_file',
            'accounts_file',
            'reinsurance_scope_file',
            'reinsurance_info_file'
        )

    def get_serializer_class(self):
        action_serializer_map = {
            'create_analysis': CreateAnalysisSerializer,
            'list': PortfolioListSerializer,
            'set_storage_links': PortfolioStorageSerializer,
            'storage_links': PortfolioStorageSerializer,
            'validate': PortfolioValidationSerializer,
            'accounts_file': RelatedFileSerializer,
            'location_file': RelatedFileSerializer,
            'reinsurance_info_file': RelatedFileSerializer,
            'reinsurance_scope_file': RelatedFileSerializer,
            'file_sql': FileSQLSerializer,
            'exposure_run': ExposureRunSerializer,
            'exposure_transform': ExposureTransformSerializer,
        }
        return action_serializer_map.get(self.action, super().get_serializer_class())

    @property
    def parser_classes(self):
        upload_views = ['accounts_file', 'location_file', 'reinsurance_info_file', 'reinsurance_scope_file', 'exposure_transform']
        if getattr(self, 'action', None) in upload_views:
            return [MultiPartParser]
        else:
            return api_settings.DEFAULT_PARSER_CLASSES

    @action(methods=['post'], detail=True)
    def create_analysis(self, request, pk=None, version=None):
        """
        Creates an analysis object from the portfolio.
        """
        portfolio = self.get_object()
        serializer = self.get_serializer(data=request.data, portfolio=portfolio, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        if 'groups' in validated_data:
            del validated_data['groups']
        analysis = serializer.create(serializer.validated_data)
        analysis.generate_inputs(request.user)

        return Response(
            AnalysisSerializer(instance=analysis, context=self.get_serializer_context()).data,
            status=HTTP_201_CREATED,
        )

    @extend_schema(methods=['post'], request=StorageLinkSerializer)
    @action(methods=['get', 'post'], detail=True)
    def storage_links(self, request, pk=None, version=None):
        """
        get:
        Gets the portfolios storage backed link references, `object keys` or `file paths`
        """
        method = request.method.lower()
        if method == 'get':
            serializer = self.get_serializer(self.get_object())
            return Response(serializer.data)
        else:
            serializer = self.get_serializer(self.get_object(), data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

    @extend_schema(methods=['get'], responses={200: FILE_RESPONSE}, parameters=[FILE_HEADERS, FILE_FORMAT_PARAM])
    @extend_schema(methods=['post'], parameters=[FILE_VALIDATION_PARAM])
    @action(methods=['get', 'post', 'delete'], detail=True)
    def accounts_file(self, request, pk=None, version=None):
        """
        get:
        Gets the portfolios `accounts_file` contents

        post:
        Sets the portfolios `accounts_file` contents

        delete:
        Disassociates the portfolios `accounts_file` with the portfolio
        """
        method = request.method.lower()
        if method == 'post':
            store_as_parquet = django_settings.PORTFOLIO_PARQUET_STORAGE
            oed_validate = request.GET.get('validate', str(django_settings.PORTFOLIO_UPLOAD_VALIDATION)).lower() == 'true'
        else:
            store_as_parquet = None
            oed_validate = None
        return handle_related_file(self.get_object(), 'accounts_file', request, self.supported_mime_types, store_as_parquet, oed_validate)

    @extend_schema(methods=['get'], responses={200: FILE_RESPONSE}, parameters=[FILE_HEADERS, FILE_FORMAT_PARAM])
    @extend_schema(methods=['post'], parameters=[FILE_VALIDATION_PARAM])
    @action(methods=['get', 'post', 'delete'], detail=True)
    def location_file(self, request, pk=None, version=None):
        """
        get:
        Gets the portfolios `location_file` contents

        post:
        Sets the portfolios `location_file` contents

        delete:
        Disassociates the portfolios `location_file` contents
        """
        method = request.method.lower()
        if method == 'post':
            store_as_parquet = django_settings.PORTFOLIO_PARQUET_STORAGE
            oed_validate = request.GET.get('validate', str(django_settings.PORTFOLIO_UPLOAD_VALIDATION)).lower() == 'true'
        else:
            store_as_parquet = None
            oed_validate = None
        return handle_related_file(self.get_object(), 'location_file', request, self.supported_mime_types, store_as_parquet, oed_validate)

    @extend_schema(methods=['get'], responses={200: FILE_RESPONSE}, parameters=[FILE_HEADERS, FILE_FORMAT_PARAM])
    @extend_schema(methods=['post'], parameters=[FILE_VALIDATION_PARAM])
    @action(methods=['get', 'post', 'delete'], detail=True)
    def reinsurance_info_file(self, request, pk=None, version=None):
        """
        get:
        Gets the portfolios `reinsurance_info_file` contents

        post:
        Sets the portfolios `reinsurance_info_file` contents

        delete:
        Disassociates the portfolios `reinsurance_info_file` contents
        """
        method = request.method.lower()
        if method == 'post':
            store_as_parquet = django_settings.PORTFOLIO_PARQUET_STORAGE
            oed_validate = request.GET.get('validate', str(django_settings.PORTFOLIO_UPLOAD_VALIDATION)).lower() == 'true'
        else:
            store_as_parquet = None
            oed_validate = None
        return handle_related_file(self.get_object(), 'reinsurance_info_file', request, self.supported_mime_types, store_as_parquet, oed_validate)

    @extend_schema(methods=['get'], responses={200: FILE_RESPONSE}, parameters=[FILE_HEADERS, FILE_FORMAT_PARAM])
    @extend_schema(methods=['post'], parameters=[FILE_VALIDATION_PARAM])
    @action(methods=['get', 'post', 'delete'], detail=True)
    def reinsurance_scope_file(self, request, pk=None, version=None):
        """
        get:
        Gets the portfolios `reinsurance_scope_file` contents

        post:
        Sets the portfolios `reinsurance_scope_file` contents

        delete:
        Disassociates the portfolios `reinsurance_scope_file` contents
        """
        method = request.method.lower()
        if method == 'post':
            store_as_parquet = django_settings.PORTFOLIO_PARQUET_STORAGE
            oed_validate = request.GET.get('validate', str(django_settings.PORTFOLIO_UPLOAD_VALIDATION)).lower() == 'true'
        else:
            store_as_parquet = None
            oed_validate = None
        return handle_related_file(self.get_object(), 'reinsurance_scope_file', request, self.supported_mime_types, store_as_parquet, oed_validate)

    @action(methods=['get', 'post'], detail=True)
    def validate(self, request, pk=None, version=None):
        """
        get:
        Return OED validation status for each attached file

        post:
        Run OED validation on the connected exposure files
        """
        method = request.method.lower()
        instance = self.get_object()

        if method == 'post':
            instance.run_oed_validation(user_pk=request.user.pk)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @extend_schema(methods=['get'], responses={200: FILE_RESPONSE}, parameters=FILE_HEADERS)
    @extend_schema(methods=['post'], request=ExposureRunSerializer)
    @action(methods=['get', 'post'], detail=True)
    def exposure_run(self, request, pk=None, version=None):
        """
        get:
        Return result of `oasislmf exposure run` on the targetted portfolio

        post:
        Starts a run of `oasislmf exposure run` with the given parameters.
        Parameters can be viewed with command `oasislmf exposure run -h`.
        """
        method = request.method.lower()
        instance = self.get_object()

        if method == 'get':
            return handle_related_file(self.get_object(), 'exposure_run_file', request, ['text/csv'])

        instance.exposure_run(request.data.get('params'), request.user.pk)
        return Response({"message": "in queue"})

    @extend_schema(methods=['post'], request=ExposureTransformSerializer)
    @action(methods=['post'], detail=True)
    def exposure_transform(self, request, pk=None, version=None):
        """
        post:
        Converts data to between OED and AIR
        """
        instance = self.get_object()
        instance.transform_file = RelatedFile.objects.create(
            file=request.data['transform_file'], content_type='text/csv', creator=request.user,
            filename='transform_file_delete_on_use', store_as_filename=True
        )
        instance.mapping_file = RelatedFile.objects.create(
            file=request.data['mapping_file'], content_type='text/yaml', creator=request.user,
            filename='mapping_file_delete_on_use', store_as_filename=True
        )
        instance.exposure_transform(request)
        return Response({"message": "in queue"})

    @extend_schema(methods=['get'], responses={200: FILE_RESPONSE}, parameters=FILE_HEADERS)
    @action(methods=['get'], detail=True)
    def errors_file(self, request, pk=None, version=None):
        return handle_related_file(self.get_object(), 'run_errors_file', request, ['text/csv'])

    # LOT3 DISABLE
    # @requires_sql_reader
    # @swagger_auto_schema(methods=['post'], responses={200: FILE_RESPONSE}, manual_parameters=[FILE_FORMAT_PARAM])
    # @action(methods=['post'], url_path=r'(?P<file>\w+)/sql', detail=True)
    # def file_sql(self, request, *args, **kwargs):
    #     """
    #     post:
    #     Gets the sql for  `<>_file` contents
    #     """
    #     serializer = self.get_serializer(self.get_object(), data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     sql = serializer.validated_data.get("sql")

    #     return handle_related_file_sql(self.get_object(), kwargs["file"], request, sql)
