from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
# from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.settings import api_settings

from ..files.serializers import RelatedFileSerializer
from ..files.views import handle_related_file
from ..filters import TimeStampedFilter
from .models import DataFile
from ..permissions.group_auth import VerifyGroupAccessModelViewSet
from ..schemas.custom_swagger import FILE_RESPONSE
from .serializers import DataFileSerializer, DataFileListSerializer


class DataFileFilter(TimeStampedFilter):
    filename = filters.CharFilter(
        help_text=_('Filter results by case insensitive `filename` equal to the given string'),
        lookup_expr='iexact',
        field_name='file__filename'
    )
    filename__contains = filters.CharFilter(
        help_text=_('Filter results by case insensitive `filename` containing the given string'),
        lookup_expr='icontains',
        field_name='file__filename'
    )
    content_type = filters.CharFilter(
        help_text=_('Filter results by case insensitive `content_type` equal to the given string'),
        lookup_expr='iexact',
        field_name='file__content_type'
    )
    content_type__contains = filters.CharFilter(
        help_text=_('Filter results by case insensitive `content_type` containing the given string'),
        lookup_expr='icontains',
        field_name='file__content_type'
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
    file_category = filters.CharFilter(
        help_text=_('Filter results by case insensitive `file_category` equal to the given string'),
        lookup_expr='iexact',
        field_name='file_category'
    )
    file_category__contains = filters.CharFilter(
        help_text=_('Filter results by case insensitive `file_category` containing the given string'),
        lookup_expr='icontains',
        field_name='file_category'
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
            'file_category',
            'file_category__contains',
            'user',
        ]


class DataFileViewset(VerifyGroupAccessModelViewSet):

    serializer_class = DataFileSerializer
    filterset_class = DataFileFilter

    group_access_model = DataFile

    def get_queryset(self):
        return super().get_queryset().select_related('file')

    def get_serializer_class(self):
        if self.action in ['content', 'set_content']:
            return RelatedFileSerializer
        elif self.action in ['list']:
            return DataFileListSerializer
        else:
            return super(DataFileViewset, self).get_serializer_class()

    @property
    def parser_classes(self):
        if getattr(self, 'action', None) in ['set_content']:
            return [MultiPartParser]
        else:
            return api_settings.DEFAULT_PARSER_CLASSES

    @swagger_auto_schema(methods=['get'], responses={200: FILE_RESPONSE})
    @action(methods=['get', 'delete'], detail=True)
    def content(self, request, pk=None, version=None):
        """
        get:
        Gets the data file's file contents

        delete:
        Deletes the data file.
        """

        file_response = handle_related_file(self.get_object(), 'file', request, None)
        return file_response

    @content.mapping.post
    def set_content(self, request, pk=None, version=None):
        """
        post:
        Sets the data file's `file` contents
        """

        return handle_related_file(self.get_object(), 'file', request, None)
