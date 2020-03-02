import coreschema
import six
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from django_filters.fields import ModelMultipleChoiceField, MultipleChoiceField
from django_filters.filters import QuerySetRequestMixin
from django_filters.rest_framework import DjangoFilterBackend, MultipleChoiceFilter


class TimeStampedFilter(filters.FilterSet):
    created = filters.DateFilter(help_text=_('Filter results by results created at the given time'))
    created__date = filters.DateFilter(
        help_text=_('Filter results by results created on the given date'),
        lookup_expr='date',
        field_name='created',
    )
    created__gte = filters.DateFilter(
        help_text=_('Filter results by results created after or at the the given time'),
        lookup_expr='gte',
        field_name='created'
    )
    created__lte = filters.DateFilter(
        help_text=_('Filter results by results created before or at the given time'),
        lookup_expr='lte',
        field_name='created'
    )
    created__gt = filters.DateFilter(
        help_text=_('Filter results by results created after the given time'),
        lookup_expr='gt',
        field_name='created'
    )
    created__lt = filters.DateFilter(
        help_text=_('Filter results by results created before the given time'),
        lookup_expr='lt',
        field_name='created'
    )
    modified = filters.DateFilter(help_text=_('Filter results by results modified at the given time'))
    modified__date = filters.DateFilter(
        help_text=_('Filter results by results modified on the given date'),
        lookup_expr='date',
        field_name='modified'
    )
    modified__gte = filters.DateFilter(
        help_text=_('Filter results by results modified after or at the the given time'),
        lookup_expr='gte',
        field_name='modified'
    )
    modified__lte = filters.DateFilter(
        help_text=_('Filter results by results modified before or at the given time'),
        lookup_expr='lte',
        field_name='modified'
    )
    modified__gt = filters.DateFilter(
        help_text=_('Filter results by results modified after the given time'),
        lookup_expr='gt',
        field_name='modified'
    )
    modified__lt = filters.DateFilter(
        help_text=_('Filter results by results modified before the given time'),
        lookup_expr='lt',
        field_name='modified'
    )


class Backend(DjangoFilterBackend):
    def get_coreschema_field(self, field):
        description = six.text_type(field.extra.get('help_text', ''))

        if isinstance(field, filters.NumberFilter):
            return coreschema.Number(description=description)
        elif isinstance(field, filters.MultipleChoiceFilter):
            return coreschema.Array(
                items=coreschema.Enum(enum=[c[0] for c in field.field.choices]),
                description=description,
                unique_items=True,
            )
        elif isinstance(field, filters.ChoiceFilter):
            return coreschema.Enum(
                enum=[c[0] for c in field.field.choices],
                description=description
            )
        else:
            return coreschema.String(description=description)


class CsvMultipleChoiceMixin(object):
    def to_python(self, value):
        if value and len(value) == 1 and ',' in value[0]:
            return super(CsvMultipleChoiceMixin, self).to_python(value[0].split(','))
        else:
            return super(CsvMultipleChoiceMixin, self).to_python(value)


class CsvMultipleChoiceField(CsvMultipleChoiceMixin, MultipleChoiceField):
    pass


class CsvModelMultipleChoiceField(CsvMultipleChoiceMixin, ModelMultipleChoiceField):
    pass


class CsvMultipleChoiceFilter(MultipleChoiceFilter):
    field_class = CsvMultipleChoiceField


class CsvModelMultipleChoiceFilter(QuerySetRequestMixin, CsvMultipleChoiceFilter):
    field_class = CsvModelMultipleChoiceField
