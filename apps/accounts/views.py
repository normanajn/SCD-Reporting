from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, UpdateView

from .permissions import AdminRequiredMixin

User = get_user_model()


class ProfileView(AdminRequiredMixin, UpdateView):
    model = User
    fields = ['display_name', 'employee_id']
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('profile')

    # Override test_func from AdminRequiredMixin — profile is for all auth users
    def test_func(self):
        return self.request.user.is_authenticated

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Profile updated.')
        return super().form_valid(form)


class AdminUsersView(AdminRequiredMixin, ListView):
    model = User
    template_name = 'accounts/admin_users.html'
    context_object_name = 'users'
    ordering = ['email']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['role_choices'] = User.Role.choices
        return ctx


class UserRoleUpdateView(AdminRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        role = request.POST.get('role', '')
        if role in User.Role.values:
            user.role = role
            user.save(update_fields=['role'])
        return render(request, 'accounts/partials/_role_select.html', {
            'u': user,
            'role_choices': User.Role.choices,
        })
