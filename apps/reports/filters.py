import django_filters

from apps.entries.models import WorkItem
from apps.taxonomy.models import Category, Project


class WorkItemFilter(django_filters.FilterSet):
    author_email = django_filters.CharFilter(
        field_name='author__email',
        lookup_expr='icontains',
        label='Author email',
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
    is_private = django_filters.BooleanFilter(label='Private only')

    class Meta:
        model = WorkItem
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use plain DateInput for date fields
        import django.forms as forms
        for fname in ('period_after', 'period_before'):
            self.filters[fname].field.widget = forms.DateInput(attrs={'type': 'date'})
