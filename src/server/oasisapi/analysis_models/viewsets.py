from __future__ import absolute_import

from django.utils.translation import ugettext_lazy as _
from django_filters import rest_framework as filters
from rest_framework import viewsets

from ..filters import TimeStampedFilter
from .models import AnalysisModel
from .serializers import AnalysisModelSerializer


class AnalysisModelFilter(TimeStampedFilter):
    supplier_id = filters.CharFilter(
        help_text=_('Filter results by case insensitive `supplier_id` equal to the given string'),
        lookup_expr='iexact'
    )
    supplier_id__contains = filters.CharFilter(
        help_text=_('Filter results by case insensitive `supplier_id` containing the given string'),
        lookup_expr='icontains',
        field_name='name'
    )
    version_id = filters.CharFilter(
        help_text=_('Filter results by case insensitive `version_id` equal to the given string'),
        lookup_expr='iexact'
    )
    version_id__contains = filters.CharFilter(
        help_text=_('Filter results by case insensitive `version_id` containing the given string'),
        lookup_expr='icontains',
        field_name='name'
    )

    class Meta:
        model = AnalysisModel
        fields = [
            'supplier_id',
            'supplier_id__contains',
            'version_id',
            'version_id__contains',
        ]


class AnalysisModelViewSet(viewsets.ModelViewSet):
    """
    list:
    Returns a list of Model objects.

    ### Examples

    To get all models with 'foo' in their name

        /models/?supplier_id__contains=foo

    To get all models with 'bar' in their name

        /models/?version_id__contains=bar

    To get all models created on 1970-01-01

        /models/?created__date=1970-01-01

    To get all models updated before 2000-01-01

        /models/?modified__lt=2000-01-01

    retrieve:
    Returns the specific model entry.

    create:
    Creates a model based on the input data

    update:
    Updates the specified model

    partial_update:
    Partially updates the specified model (only provided fields are updated)
    """

    queryset = AnalysisModel.objects.all()
    serializer_class = AnalysisModelSerializer
    filter_class = AnalysisModelFilter
