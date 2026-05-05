from django import forms

from .models import Category, Project


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
