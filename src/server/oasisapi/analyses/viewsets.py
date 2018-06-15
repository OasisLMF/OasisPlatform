from __future__ import absolute_import

from rest_framework import viewsets

from .models import Analysis
from .serializers import AnalysisSerializer


class AnalysisViewSet(viewsets.ModelViewSet):
    queryset = Analysis.objects.all()
    serializer_class = AnalysisSerializer

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super(AnalysisViewSet, self).update(request, *args, **kwargs)
