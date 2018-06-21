from __future__ import absolute_import

from rest_framework import viewsets

from .models import AnalysisModel
from .serializers import AnalysisModelSerializer


class AnalysisModelViewSet(viewsets.ModelViewSet):
    """ Returns a list of Analysis Model objects """

    queryset = AnalysisModel.objects.all()
    serializer_class = AnalysisModelSerializer

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super(AnalysisModelViewSet, self).update(request, *args, **kwargs)
