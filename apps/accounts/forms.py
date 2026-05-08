from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from apps.taxonomy.models import WorkGroup

from .models import User


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['display_name', 'employee_id', 'group']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['group'].queryset = WorkGroup.objects.filter(is_active=True).order_by('sort_order', 'name')
        self.fields['group'].required = False
        self.fields['group'].empty_label = '— No group —'


class AdminCreateUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm password')

    class Meta:
        model = User
        fields = ['email', 'display_name', 'employee_id', 'group', 'role']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['group'].queryset = WorkGroup.objects.filter(is_active=True).order_by('sort_order', 'name')
        self.fields['group'].required = False
        self.fields['group'].empty_label = '— No group —'
        self.fields['display_name'].required = False
        self.fields['employee_id'].required = False

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Passwords do not match.')
        elif p1:
            # Build an unsaved user so validators can check similarity to email etc.
            user = User(email=cleaned.get('email', ''), username=cleaned.get('email', ''))
            try:
                validate_password(p1, user=user)
            except ValidationError as e:
                self.add_error('password', e)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        if commit:
            user.save()
        return user
