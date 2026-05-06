from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
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


class UserSetPasswordView(AdminRequiredMixin, View):
    template_name = 'accounts/set_password.html'

    def _get_target(self, pk):
        return get_object_or_404(User, pk=pk)

    def get(self, request, pk):
        return render(request, self.template_name, {'target': self._get_target(pk)})

    def post(self, request, pk):
        target = self._get_target(pk)
        p1 = request.POST.get('new_password1', '')
        p2 = request.POST.get('new_password2', '')
        if not p1:
            messages.error(request, 'Password cannot be empty.')
            return render(request, self.template_name, {'target': target})
        if p1 != p2:
            messages.error(request, 'Passwords do not match.')
            return render(request, self.template_name, {'target': target})
        target.set_password(p1)
        target.save(update_fields=['password'])
        messages.success(request, f'Password updated for {target.email}.')
        return redirect('admin-users')


class UserDeleteView(AdminRequiredMixin, View):
    template_name = 'accounts/confirm_delete_user.html'

    def _get_target(self, pk):
        return get_object_or_404(User, pk=pk)

    def get(self, request, pk):
        target = self._get_target(pk)
        if target == request.user:
            messages.error(request, 'You cannot delete your own account.')
            return redirect('admin-users')
        return render(request, self.template_name, {'target': target})

    def post(self, request, pk):
        target = self._get_target(pk)
        if target == request.user:
            messages.error(request, 'You cannot delete your own account.')
            return redirect('admin-users')
        email = target.email
        try:
            target.delete()
            messages.success(request, f'Account "{email}" has been deleted.')
        except ProtectedError:
            messages.error(
                request,
                f'Cannot delete "{email}" — they have existing entries. '
                'Remove or reassign their entries first.',
            )
        return redirect('admin-users')
