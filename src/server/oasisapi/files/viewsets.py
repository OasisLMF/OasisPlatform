from __future__ import absolute_import

from django.http import JsonResponse, Http404, StreamingHttpResponse, HttpResponse
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError

from ..filters import TimeStampedFilter
from .serializers import RelatedFileSerializer, ConvertSerializer, MappingFileSerializer
from .models import RelatedFile, MappingFile
from ..permissions.group_auth import verify_user_is_in_obj_groups


class FilesFilter(TimeStampedFilter):
    content_type = filters.CharFilter(
        help_text=_('Filter results by case insensitive `supplier_id` equal to the given string'),
        lookup_expr='iexact',
        field_name='content_type'
    )
    filename__contains = filters.CharFilter(
        help_text=_('Filter results by case insensitive `supplier_id` containing the given string'),
        lookup_expr='icontains',
        field_name='filename'
    )
    user = filters.CharFilter(
        help_text=_('Filter results by case insensitive `model_id` equal to the given string'),
        lookup_expr='iexact',
        field_name='creator_name'
    )

    class Meta:
        model = RelatedFile
        fields = [
            'content_type',
            'filename__contains',
            'user',
        ]


class FilesViewSet(viewsets.GenericViewSet):
    """ Add doc string here
    """
    queryset = RelatedFile.objects.all()
    serializer_class = RelatedFileSerializer
    filterset_class = FilesFilter

    group_access_model = RelatedFile

    @action(methods=['get'], detail=True)
    def conversion_log_file(self, request, **kwargs):
        instance = self.get_object()
        if not instance.conversion_log_file:
            raise Http404()

        verify_user_is_in_obj_groups(request.user, instance, 'You dont have permission to read the log file')
        return HttpResponse(instance.conversion_log_file.read(), content_type="text/plain")

    @action(methods=['post'], detail=True, serializer_class=ConvertSerializer)
    def convert(self, request, pk=None, version=None):
        instance = self.get_object()

        verify_user_is_in_obj_groups(request.user, instance, 'You dont have permission to ru a conversion on the file')
        if not RelatedFile.ConversionState.is_ready(instance.conversion_state):
            raise ValidationError(
                "File is not in a convertable state. " +
                "Current conversion state is " +
                RelatedFile.ConversionState[instance.conversion_state]
            )

        serializer = ConvertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        instance.start_conversion(MappingFile.objects.get(id=serializer.validated_data["mapping_file"]))

        return JsonResponse(RelatedFileSerializer(instance).data)


@swagger_auto_schema(methods=['post'])
class MappingFilesViewSet(viewsets.ModelViewSet):
    parser_classes = (MultiPartParser,)

    queryset = MappingFile.objects.all()
    serializer_class = MappingFileSerializer

    # TODO: add endpoints for accessing mapping and validation files
    # TODO: add permissions
