from __future__ import absolute_import

from django.utils.translation import ugettext_lazy as _
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.status import HTTP_201_CREATED

from ..filters import TimeStampedFilter
from ..analyses.serializers import AnalysisSerializer
from ..files.views import handle_related_file
from ..files.serializers import RelatedFileSerializer
from .models import Portfolio
from .serializers import PortfolioSerializer, CreateAnalysisSerializer


class PortfolioFilter(TimeStampedFilter):
    name = filters.CharFilter(help_text=_('Filter results by case insensitive names equal to the given string'), lookup_expr='iexact')
    name__contains = filters.CharFilter(help_text=_('Filter results by case insensitive name containing the given string'), lookup_expr='icontains', field_name='name')
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


class PortfolioViewSet(viewsets.ModelViewSet):
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

    queryset = Portfolio.objects.all()
    serializer_class = PortfolioSerializer
    filter_class = PortfolioFilter

    def get_serializer_class(self):
        if self.action == 'create_analysis':
            return CreateAnalysisSerializer
        elif self.action in ['accounts_file', 'location_file', 'reinsurance_info_file', 'reinsurance_scope_file']:
            return RelatedFileSerializer
        else:
            return super(PortfolioViewSet, self).get_serializer_class()

    @property
    def parser_classes(self):
        if getattr(self, 'action', None) in ['accounts_file', 'location_file', 'reinsurance_info_file', 'reinsurance_scope_file']:
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
        analysis = serializer.create(serializer.validated_data)
        analysis.generate_inputs(request.user)

        return Response(
            AnalysisSerializer(instance=analysis, context=self.get_serializer_context()).data,
            status=HTTP_201_CREATED,
        )

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
        return handle_related_file(self.get_object(), 'accounts_file', request, ['application/json', 'text/csv'])

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
        return handle_related_file(self.get_object(), 'location_file', request, ['application/json', 'text/csv'])

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
        return handle_related_file(self.get_object(), 'reinsurance_info_file', request, ['application/json', 'text/csv'])

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
        return handle_related_file(self.get_object(), 'reinsurance_scope_file', request, ['application/json', 'text/csv'])
