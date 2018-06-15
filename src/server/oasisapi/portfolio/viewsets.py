from __future__ import absolute_import

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED

from ..analysis.serializers import AnalysisSerializer
from .models import Portfolio
from .serializers import PortfolioSerializer


class PortfolioViewSet(viewsets.ModelViewSet):
    queryset = Portfolio.objects.all()
    serializer_class = PortfolioSerializer

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super(PortfolioViewSet, self).update(request, *args, **kwargs)

    @action(methods=['post'], detail=True)
    def create_analysis(self, request, pk=None):
        portfolio = self.get_object()

        data = request.data.copy()
        data['portfolio'] = portfolio.pk

        serializer = AnalysisSerializer(data=data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        analysis = serializer.create(serializer.validated_data)

        return Response(
            AnalysisSerializer(instance=analysis).data,
            status=HTTP_201_CREATED,
        )
