from django import forms
from django.db.models import F

from apps.taxonomy.models import Category, Project, Tag, WorkGroup

from .models import WorkItem


class WorkItemForm(forms.ModelForm):
    tags_input = forms.CharField(required=False, widget=forms.HiddenInput(), label='')

    class Meta:
        model = WorkItem
        fields = [
            'title', 'project', 'category', 'group',
            'period_kind', 'period_start', 'period_end',
            'description', 'is_private', 'is_critical', 'is_highlight', 'highlight_stars',
        ]
        widgets = {
            'period_kind':    forms.HiddenInput(),
            'period_start':   forms.DateInput(attrs={'type': 'date'}),
            'period_end':     forms.DateInput(attrs={'type': 'date'}),
            'description':    forms.Textarea(attrs={'rows': 8}),
            'highlight_stars': forms.HiddenInput(),
        }

    DESCRIPTION_TEMPLATE = "Project Milestone:\nPerformance Goal: \nUpdate:\n\n<Repeat as needed>"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].queryset  = Project.objects.filter(is_active=True).order_by('sort_order', 'name')
        self.fields['category'].queryset = Category.objects.filter(is_active=True).order_by('sort_order', 'name')
        self.fields['group'].queryset      = WorkGroup.objects.filter(is_active=True).order_by('sort_order', 'name')
        self.fields['group'].required      = False
        self.fields['highlight_stars'].required = False
        if self.instance.pk:
            self.fields['tags_input'].initial = ','.join(
                self.instance.tags.values_list('name', flat=True)
            )
        else:
            self.fields['description'].initial = self.DESCRIPTION_TEMPLATE

    def clean_highlight_stars(self):
        val = self.cleaned_data.get('highlight_stars')
        return val if val is not None else 0

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('period_start')
        end   = cleaned.get('period_end')
        if start and end and end < start:
            raise forms.ValidationError('Period end must be on or after period start.')
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            self._sync_tags(instance)
        return instance

    def _sync_tags(self, instance):
        raw = self.cleaned_data.get('tags_input', '')
        new_names = {t.strip().lower() for t in raw.split(',') if t.strip()}

        old_ids = set(instance.tags.values_list('id', flat=True))

        new_tags = []
        for name in new_names:
            tag, _ = Tag.objects.get_or_create(name=name)
            new_tags.append(tag)
        new_ids = {t.id for t in new_tags}

        added   = new_ids - old_ids
        removed = old_ids - new_ids
        if added:
            Tag.objects.filter(id__in=added).update(use_count=F('use_count') + 1)
        if removed:
            Tag.objects.filter(id__in=removed).update(use_count=F('use_count') - 1)

        instance.tags.set(new_tags)
