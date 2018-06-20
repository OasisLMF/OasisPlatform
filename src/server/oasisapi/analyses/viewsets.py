from __future__ import absolute_import

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

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
        return Response(self.get_serializer(instance=obj).data)

    @action(methods=['post'], detail=True)
    def cancel(self, request, pk=None):
        obj = self.get_object()
        obj.cancel()
        return Response(self.get_serializer(instance=obj).data)
