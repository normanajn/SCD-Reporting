from django import forms

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
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        if commit:
            user.save()
        return user
