from django.utils.translation import ugettext_lazy as _
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.settings import api_settings

from ..files.serializers import RelatedFileSerializer
from ..files.views import handle_related_file
from ..filters import TimeStampedFilter
from .models import DataFile
from .serializers import DataFileSerializer


class DataFileFilter(TimeStampedFilter):
    filename = filters.CharFilter(
        help_text=_('Filter results by case insensitive `filename` equal to the given string'),
        lookup_expr='iexact',
        field_name='filename'
    )
    filename__contains = filters.CharFilter(
        help_text=_('Filter results by case insensitive `filename` containing the given string'),
        lookup_expr='icontains',
        field_name='filename'
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
        model = DataFile
        fields = [
            'filename',
            'filename__contains',
            'file_description',
            'file_description__contains',
            'user',
        ]


class DataFileViewset(viewsets.ModelViewSet):
    queryset = DataFile.objects.all()
    serializer_class = DataFileSerializer
    filter_class = DataFileFilter

    def get_serializer_class(self):
        if self.action in ['content']:
            return RelatedFileSerializer
        else:
            return super(DataFileViewset, self).get_serializer_class()

    @property
    def parser_classes(self):
        if getattr(self, 'action', None) in ['content']:
            return [MultiPartParser]
        else:
            return api_settings.DEFAULT_PARSER_CLASSES

    @action(methods=['get', 'post', 'delete'], detail=True)
    def content(self, request, pk=None, version=None):
        """
        get:
        Gets the data file's file contents

        post:
        Sets the data file's `file` contents

        delete:
        Deletes the data file.
        """

        file_response = handle_related_file(self.get_object(), 'file', request, None)
        return file_response
