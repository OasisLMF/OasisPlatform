from __future__ import absolute_import

import io
import json
import os

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from django.http import JsonResponse, Http404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.settings import api_settings

from .models import AnalysisModel
from .serializers import AnalysisModelSerializer, ModelVersionsSerializer

from ..data_files.serializers import DataFileSerializer
from ..filters import TimeStampedFilter
from ..files.views import handle_related_file, handle_json_data
from ..files.serializers import RelatedFileSerializer
from ..schemas.custom_swagger import FILE_RESPONSE
from ..schemas.serializers import ModelParametersSerializer


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
    filterset_class = AnalysisModelFilter

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

    @swagger_auto_schema(methods=['get'], responses={200: FILE_RESPONSE})
    @action(methods=['get', 'delete'], detail=True)
    def resource_file(self, request, pk=None, version=None):
        """
        get:
        Gets the models `resource_file` contents

        delete:
        Disassociates the moodels `resource_file` contents
        """
        try:
            return handle_related_file(self.get_object(), 'resource_file', request, ['application/json'])
        except Http404:
            print("No resource_file set, returning default file as response")
            with io.open(os.path.join(settings.STATIC_ROOT, 'model_resource.json')) as default_resource:
                data = json.load(default_resource)
            response = JsonResponse(data)
            response['Content-Disposition'] = 'attachment; filename="{}"'.format('default_resource_file.json')
            return response

    @resource_file.mapping.post
    def set_resource_file(self, request, pk=None, version=None):
        """
        post:
        Sets the models `resource_file` contents
        """
        return handle_related_file(self.get_object(), 'resource_file', request, ['application/json'])

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
        return handle_json_data(self.get_object(), 'resource_file', request, ModelParametersSerializer)
