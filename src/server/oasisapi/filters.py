from django_filters import rest_framework as filters


class CreatedModifiedFilterSet(filters.FilterSet):
    created_lte = filters.DateTimeFilter(name='created', lookup_expr='lte')
    created_gte = filters.DateTimeFilter(name='created', lookup_expr='gte')
    modified_lte = filters.DateTimeFilter(name='modified', lookup_expr='lte')
    modified_gte = filters.DateTimeFilter(name='modified', lookup_expr='gte')

    class Meta:
        fields = [
            'created',
            'modified',
            'created_lte',
            'created_gte',
            'modified_gte',
            'modified_gte',
        ]
