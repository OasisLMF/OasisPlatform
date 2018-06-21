from __future__ import absolute_import

from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED

from ..analyses.serializers import AnalysisSerializer
from ..filters import CreatedModifiedFilterSet
from .models import Portfolio
from .serializers import PortfolioSerializer


class PortfolioFilter(CreatedModifiedFilterSet):
    class Meta:
        model = Portfolio
        fields = [
            'id',
            'name',
            'created',
            'modified',
        ]


class PortfolioViewSet(viewsets.ModelViewSet):
    """ Returns a list of Portfolio objects \n

        ### Available filters
        - id
        - name
        - created, created_lte, created_gte
        - modified, modified_lte, modified_gte

        `e.g. ?created_gte=2018-01-01&created_lte=2018-02-01`
    """

    queryset = Portfolio.objects.all()
    serializer_class = PortfolioSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = PortfolioFilter

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
