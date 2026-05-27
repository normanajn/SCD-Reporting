import shlex

import django_filters
from django.db.models import Q

from apps.entries.models import WorkItem
from apps.taxonomy.models import Category, LabPriority, Project, WorkGroup


class WorkItemFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(
        method='filter_search',
        label='Search',
    )
    author_email = django_filters.CharFilter(
        field_name='author__email',
        lookup_expr='icontains',
        label='Author email',
    )
    group = django_filters.ModelChoiceFilter(
        queryset=WorkGroup.objects.filter(is_active=True).order_by('sort_order', 'name'),
        label='Group',
        empty_label='All groups',
    )
    project = django_filters.ModelChoiceFilter(
        queryset=Project.objects.filter(is_active=True).order_by('sort_order', 'name'),
        label='Project',
        empty_label='All projects',
    )
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.filter(is_active=True).order_by('sort_order', 'name'),
        label='Category',
        empty_label='All categories',
    )
    lab_priority = django_filters.ModelChoiceFilter(
        queryset=LabPriority.objects.filter(is_active=True).order_by('sort_order', 'name'),
        label='Lab Priority',
        empty_label='All lab priorities',
    )
    period_after = django_filters.DateFilter(
        field_name='period_start',
        lookup_expr='gte',
        label='Period start on/after',
        widget=django_filters.widgets.DateRangeWidget,
    )
    period_before = django_filters.DateFilter(
        field_name='period_end',
        lookup_expr='lte',
        label='Period end on/before',
    )
    is_private      = django_filters.BooleanFilter(label='Private only')
    exclude_private = django_filters.BooleanFilter(
        method='filter_exclude_private',
        label='Exclude private',
    )

    def filter_search(self, queryset, name, value):
        try:
            tokens = shlex.split(value)
        except ValueError:
            tokens = value.split()

        OPERATORS = {'AND', 'OR', 'XOR'}

        # Normalise token list: insert default OR between consecutive non-operator tokens.
        # Result is always [term, OP, term, OP, ...].
        normalized = []
        prev_was_term = False
        for token in tokens:
            if token.upper() in OPERATORS:
                if prev_was_term:
                    normalized.append(token.upper())
                    prev_was_term = False
            else:
                if prev_was_term:
                    normalized.append('OR')
                normalized.append(token)
                prev_was_term = True

        if not normalized:
            return queryset

        def term_q(t):
            return Q(title__icontains=t) | Q(description__icontains=t)

        result = term_q(normalized[0])
        i = 1
        while i < len(normalized) - 1:
            op = normalized[i]
            next_q = term_q(normalized[i + 1])
            if op == 'AND':
                result = result & next_q
            elif op == 'XOR':
                result = (result | next_q) & ~(result & next_q)
            else:  # OR
                result = result | next_q
            i += 2

        return queryset.filter(result)

    def filter_exclude_private(self, queryset, name, value):
        if value:
            return queryset.filter(is_private=False)
        return queryset

    class Meta:
        model = WorkItem
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use plain DateInput for date fields
        import django.forms as forms
        for fname in ('period_after', 'period_before'):
            self.filters[fname].field.widget = forms.DateInput(attrs={'type': 'date'})
