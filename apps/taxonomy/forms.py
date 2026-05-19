from django import forms

from .models import Category, LabPriority, Project, WorkGroup


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'short_code', 'is_active', 'sort_order']
        widgets = {
            'sort_order': forms.NumberInput(attrs={'min': 0}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'short_code', 'is_active', 'sort_order']
        widgets = {
            'sort_order': forms.NumberInput(attrs={'min': 0}),
        }


class WorkGroupForm(forms.ModelForm):
    class Meta:
        model = WorkGroup
        fields = ['name', 'short_code', 'is_active', 'sort_order']
        widgets = {
            'sort_order': forms.NumberInput(attrs={'min': 0}),
        }


class LabPriorityForm(forms.ModelForm):
    class Meta:
        model = LabPriority
        fields = ['name', 'short_code', 'is_active', 'sort_order']
        widgets = {
            'sort_order': forms.NumberInput(attrs={'min': 0}),
        }
