from __future__ import absolute_import

from django.utils.translation import gettext_lazy as _
from django.utils.decorators import method_decorator
from django_filters import rest_framework as filters
from django.http import Http404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.settings import api_settings

from ..models import AnalysisModel, SettingsTemplate
from .serializers import AnalysisModelSerializer, ModelVersionsSerializer, CreateTemplateSerializer, TemplateSerializer

from ...data_files.v1_api.serializers import DataFileSerializer
from ...filters import TimeStampedFilter
from ...files.views import handle_json_data
from ...files.serializers import RelatedFileSerializer
from ...schemas.serializers import ModelParametersSerializer, AnalysisSettingsSerializer


class AnalysisModelFilter(TimeStampedFilter):
    supplier_id = filters.CharFilter(
        help_text=_('Filter results by case insensitive `supplier_id` equal to the given string'),
        lookup_expr='iexact'
    )
    supplier_id__contains = filters.CharFilter(
        help_text=_('Filter results by case insensitive `supplier_id` containing the given string'),
        lookup_expr='icontains',
        field_name='supplier_id'
    )
    model_id = filters.CharFilter(
        help_text=_('Filter results by case insensitive `model_id` equal to the given string'),
        lookup_expr='iexact'
    )
    model_id__contains = filters.CharFilter(
        help_text=_('Filter results by case insensitive `model_id` containing the given string'),
        lookup_expr='icontains',
        field_name='model_id'
    )
    version_id = filters.CharFilter(
        help_text=_('Filter results by case insensitive `version_id` equal to the given string'),
        lookup_expr='iexact'
    )
    version_id__contains = filters.CharFilter(
        help_text=_('Filter results by case insensitive `version_id` containing the given string'),
        lookup_expr='icontains',
        field_name='version_id'
    )
    user = filters.CharFilter(
        help_text=_('Filter results by case insensitive `user` equal to the given string'),
        lookup_expr='iexact',
        field_name='creator__username'
    )

    class Meta:
        model = AnalysisModel
        fields = [
            'supplier_id',
            'supplier_id__contains',
            'model_id',
            'model_id__contains',
            'version_id',
            'version_id__contains',
            'user',
        ]


@method_decorator(name='create', decorator=swagger_auto_schema(request_body=CreateTemplateSerializer))
class SettingsTemplateViewSet(viewsets.ModelViewSet):
    """
    list:
    Returns a list of analysis_settings files stored under a model as templates.

    retrieve:
    Returns the specific templates entry.

    create:
    Creates an analysis_settings template with an option to copy the settings from an analyses.

    update:
    Updates the specified template

    partial_update:
    Partially updates the template
    """
    queryset = SettingsTemplate.objects.all()
    serializer_class = TemplateSerializer

    def get_queryset(self):
        models_pk = self.kwargs.get('models_pk')
        if models_pk:
            if not models_pk.isnumeric():
                raise Http404
            try:
                template_queryset = AnalysisModel.objects.get(id=models_pk).template_files.all()
            except AnalysisModel.DoesNotExist:
                raise Http404
            return template_queryset
        else:
            return AnalysisModel.objects.none()

    def get_serializer_class(self):
        if self.action in ['create']:
            return CreateTemplateSerializer
        else:
            return super(SettingsTemplateViewSet, self).get_serializer_class()

    def list(self, request, models_pk=None, **kwargs):
        context = {'request': request}
        template_list = self.get_queryset()
        serializer = TemplateSerializer(template_list, many=True, context=context)
        return Response(serializer.data)

    def create(self, request, models_pk=None, **kwargs):
        request_data = self.request.data
        context = {'request': request}
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_template = serializer.create(serializer.validated_data)
        new_template.save()
        model = AnalysisModel.objects.get(id=models_pk)
        model.template_files.add(new_template)
        return Response(TemplateSerializer(new_template, context=context).data)

    @swagger_auto_schema(methods=['get'], responses={200: AnalysisSettingsSerializer})
    @swagger_auto_schema(methods=['post'], request_body=AnalysisSettingsSerializer, responses={201: RelatedFileSerializer})
    @action(methods=['get', 'post', 'delete'], detail=True)
    def content(self, request, pk=None, models_pk=None, version=None):
        """
        get:
        Gets the analyses template `settings` contents

        post:
        Sets the analyses template `settings` contents

        delete:
        Disassociates the  analyses template `settings_file` contents
        """
        return handle_json_data(self.get_object(), 'file', request, AnalysisSettingsSerializer)


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

    # queryset = AnalysisModel.objects.all()
    queryset = AnalysisModel.objects.exclude(run_mode='V2')
    serializer_class = AnalysisModelSerializer
    filterset_class = AnalysisModelFilter
    # lookup_field = 'id'

    def get_serializer_class(self):
        if self.action in ['resource_file', 'set_resource_file']:
            return RelatedFileSerializer
        elif self.action in ['data_files']:
            return DataFileSerializer
        elif self.action in ['versions']:
            return ModelVersionsSerializer
        else:
            return super(AnalysisModelViewSet, self).get_serializer_class()

    @property
    def parser_classes(self):
        if getattr(self, 'action', None) in ['resource_file']:
            return [MultiPartParser]
        else:
            return api_settings.DEFAULT_PARSER_CLASSES

    def create(self, *args, **kwargs):
        request_data = self.request.data
        unique_keys = ["supplier_id", "model_id", "version_id"]

        # check if the model is Soft-deleted
        if all(k in request_data for k in unique_keys):
            keys = {k: request_data[k] for k in unique_keys}
            model = AnalysisModel.all_objects.filter(**keys)
            if model.exists():
                model = model.first()
                if model.deleted:
                    # If yes, then 'restore' and update
                    model.activate(self.request)
                    return Response(AnalysisModelSerializer(instance=model,
                                    context=self.get_serializer_context()).data)

        return super(AnalysisModelViewSet, self).create(self.request)

    @action(methods=['get'], detail=True)
    def versions(self, request, pk=None, version=None):
        obj = self.get_object()
        return Response(ModelVersionsSerializer(instance=obj, context=self.get_serializer_context()).data)

    @swagger_auto_schema(responses={200: DataFileSerializer(many=True)})
    @action(methods=['get'], detail=True)
    def data_files(self, request, pk=None, version=None):
        df = self.get_object().data_files.all()
        context = {'request': request}

        df_serializer = DataFileSerializer(df, many=True, context=context)
        return Response(df_serializer.data)


class ModelSettingsView(viewsets.ModelViewSet):
    queryset = AnalysisModel.objects.all()
    serializer_class = AnalysisModelSerializer
    filterset_class = AnalysisModelFilter

    @swagger_auto_schema(method='get', responses={200: ModelParametersSerializer})
    @swagger_auto_schema(method='post', request_body=ModelParametersSerializer, responses={201: RelatedFileSerializer})
    @action(methods=['get', 'post', 'delete'], detail=True)
    def model_settings(self, request, pk=None, version=None):
        obj = self.get_object()
        response = handle_json_data(obj, 'resource_file', request, ModelParametersSerializer)
        # Update Model's execution mode if 'model_run_mode' is in model_settings.json
        if request.method.lower() == 'post':
            obj.update_run_mode()
        return response
