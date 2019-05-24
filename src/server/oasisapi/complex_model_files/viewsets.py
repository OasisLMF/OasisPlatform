from django.utils.translation import ugettext_lazy as _
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.settings import api_settings

from ..files.serializers import RelatedFileSerializer
from ..files.views import handle_related_file
from ..filters import TimeStampedFilter
from .models import ComplexModelDataFile
from .serializers import ComplexModelDataFileSerializer


class ComplexModelDataFileFilter(TimeStampedFilter):
    file_name = filters.CharFilter(
        help_text=_('Filter results by case insensitive `file_name` equal to the given string'),
        lookup_expr='iexact',
        field_name='file_name'
    )
    file_name__contains = filters.CharFilter(
        help_text=_('Filter results by case insensitive `file_name` containing the given string'),
        lookup_expr='icontains',
        field_name='file_name'
    )
    file_description = filters.CharFilter(
        help_text=_('Filter results by case insensitive `file_description` equal to the given string'),
        lookup_expr='iexact',
        field_name='file_description'
    )
    file_description__contains = filters.CharFilter(
        help_text=_('Filter results by case insensitive `file_description` containing the given string'),
        lookup_expr='icontains',
        field_name='file_description'
    )
    user = filters.CharFilter(
        help_text=_('Filter results by case insensitive `user` equal to the given string'),
        lookup_expr='iexact',
        field_name='creator__username'
    )

    class Meta:
        model = ComplexModelDataFile
        fields = [
            'file_name',
            'file_name__contains',
            'file_description',
            'file_description__contains',
            'user',
        ]


class ComplexModelDataFileViewset(viewsets.ModelViewSet):
    queryset = ComplexModelDataFile.objects.all()
    serializer_class = ComplexModelDataFileSerializer
    filter_class = ComplexModelDataFileFilter

    def get_serializer_class(self):
        if self.action in ['data_file']:
            return RelatedFileSerializer
        else:
            return super(ComplexModelDataFileViewset, self).get_serializer_class()

    @property
    def parser_classes(self):
        if getattr(self, 'action', None) in ['data_file']:
            return [MultiPartParser]
        else:
            return api_settings.DEFAULT_PARSER_CLASSES

    @action(methods=['get', 'post', 'delete'], detail=True)
    def data_file(self, request, pk=None, version=None):
        """
        get:
        Gets the complex model data file's `data_file` contents

        post:
        Sets the complex model data file's `data_file` contents

        delete:
        Deletes the complex model data file.
        """
        return handle_related_file(self.get_object(), 'data_file', request, None)
