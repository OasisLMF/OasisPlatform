from __future__ import absolute_import

from django.http import JsonResponse, Http404, StreamingHttpResponse
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied

from ..filters import TimeStampedFilter
from .serializers import RelatedFileSerializer, ConvertSerializer, MappingFileSerializer
from .models import RelatedFile, MappingFile
from ..permissions.group_auth import verify_user_is_in_obj_groups, VerifyGroupAccessModelViewSet


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

        response = StreamingHttpResponse(instance.conversion_log_file.open(), content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(instance.conversion_log_file.name)
        return response

    @action(methods=['post'], detail=True, serializer_class=ConvertSerializer)
    def convert(self, request, pk=None, version=None):
        instance = self.get_object()

        serializer = ConvertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mapping_file = MappingFile.objects.filter(id=serializer.validated_data["mapping_file"]).first()
        if not mapping_file:
            raise ValidationError(_("Mapping file does not exist."))

        verify_user_is_in_obj_groups(request.user, instance, _('You dont have permission to run a conversion on the file'))
        verify_user_is_in_obj_groups(request.user, mapping_file, _('You dont have permission to use the mapping file'))

        # check the mapping file and related file share a group or either have no groups
        instance_groups = set(instance.groups.all())
        mapping_groups = set(mapping_file.groups.all())
        user_groups = set(request.user.groups.all())

        if (instance_groups and mapping_groups) and not ((instance_groups & mapping_groups) & user_groups):
            raise PermissionDenied(_("The file and mapping do not share a group you are part of"))

        if not RelatedFile.ConversionState.is_ready(instance.conversion_state):
            raise ValidationError(
                {
                    "detail": (
                        "File is not in a convertable state. " +
                        "Current conversion state is " +
                        RelatedFile.ConversionState[instance.conversion_state]
                    )
                }
            )

        instance.start_conversion(mapping_file)

        return JsonResponse(RelatedFileSerializer(instance).data)


@swagger_auto_schema(methods=['post', 'get'])
class MappingFilesViewSet(VerifyGroupAccessModelViewSet):
    parser_classes = (MultiPartParser,)

    queryset = MappingFile.objects.all()
    serializer_class = MappingFileSerializer

    @action(methods=['get'], detail=True)
    def conversion_file(self, request, **kwargs):
        instance = self.get_object()
        if not instance.file:
            raise Http404()

        verify_user_is_in_obj_groups(request.user, instance, 'You dont have permission to read the conversion file')

        response = StreamingHttpResponse(instance.file.open(), content_type='text/yaml')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(instance.file.name)
        return response

    @action(methods=['get'], detail=True)
    def input_validation_file(self, request, **kwargs):
        instance: MappingFile = self.get_object()
        if not instance.file:
            raise Http404()

        verify_user_is_in_obj_groups(request.user, instance, 'You dont have permission to read the input validation file')

        response = StreamingHttpResponse(instance.input_validation_file.open(), content_type='text/yaml')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(instance.input_validation_file.name)
        return response

    @action(methods=['get'], detail=True)
    def output_validation_file(self, request, **kwargs):
        instance: MappingFile = self.get_object()
        if not instance.file:
            raise Http404()

        verify_user_is_in_obj_groups(request.user, instance, 'You dont have permission to read the output validation file')

        response = StreamingHttpResponse(instance.output_validation_file.open(), content_type='text/yaml')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(instance.output_validation_file.name)
        return response
