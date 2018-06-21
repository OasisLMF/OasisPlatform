from __future__ import absolute_import

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..files.views import handle_related_file
from .models import Analysis
from .serializers import AnalysisSerializer


class AnalysisViewSet(viewsets.ModelViewSet):
    queryset = Analysis.objects.all()
    serializer_class = AnalysisSerializer

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super(AnalysisViewSet, self).update(request, *args, **kwargs)

    @action(methods=['post'], detail=True)
    def run(self, request, pk=None):
        obj = self.get_object()
        obj.run(request)
        return Response(self.get_serializer(instance=obj, context=self.get_serializer_context()).data)

    @action(methods=['post'], detail=True)
    def cancel(self, request, pk=None):
        obj = self.get_object()
        obj.cancel()
        return Response(self.get_serializer(instance=obj, context=self.get_serializer_context()).data)

    @action(methods=['post'], detail=True)
    def copy(self, request, pk=None):
        obj = self.get_object()
        new_obj = obj.copy()

        serializer = self.get_serializer(instance=new_obj, data=request.data, context=self.get_serializer_context(), partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    @action(methods=['get', 'post', 'delete'], detail=True)
    def settings_file(self, request, pk=None):
        return handle_related_file(self.get_object(), 'settings_file', request, ['application/json'])

    @action(methods=['get', 'post', 'delete'], detail=True)
    def input_file(self, request, pk=None):
        return handle_related_file(self.get_object(), 'input_file', request, ['application/x-gzip', 'application/gzip', 'application/x-tar', 'application/tar'])

    @action(methods=['get', 'delete'], detail=True)
    def input_errors_file(self, request, pk=None):
        return handle_related_file(self.get_object(), 'input_errors_file', request, ['application/json', 'text/csv'])

    @action(methods=['get', 'delete'], detail=True)
    def output_file(self, request, pk=None):
        return handle_related_file(self.get_object(), 'output_file', request, ['application/x-gzip', 'application/gzip', 'application/x-tar', 'application/tar'])
