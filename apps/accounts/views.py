from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, UpdateView

from apps.taxonomy.models import WorkGroup

from .forms import AdminCreateUserForm, ProfileForm
from .models import APIToken, SiteSettings
from .permissions import AdminRequiredMixin, UserPageRequiredMixin

User = get_user_model()


class ProfileView(AdminRequiredMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('profile')

    # Override test_func from AdminRequiredMixin — profile is for all auth users
    def test_func(self):
        return self.request.user.is_authenticated

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['api_token'] = APIToken.objects.filter(user=self.request.user).first()
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Profile updated.')
        return super().form_valid(form)


class AdminUsersView(UserPageRequiredMixin, ListView):
    model = User
    template_name = 'accounts/admin_users.html'
    context_object_name = 'users'
    ordering = ['email']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['role_choices'] = User.Role.choices
        ctx['site_settings'] = SiteSettings.get_solo()
        ctx['create_form'] = AdminCreateUserForm()
        ctx['all_groups'] = WorkGroup.objects.filter(is_active=True).order_by('sort_order', 'name')
        return ctx


class UserRoleUpdateView(AdminRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden('You cannot change your own role.')
        role = request.POST.get('role', '')
        if role in User.Role.values:
            user.role = role
            user.save(update_fields=['role'])
        return render(request, 'accounts/partials/_role_update_response.html', {
            'u': user,
            'role_choices': User.Role.choices,
            'managed_group_ids':   list(user.managed_groups.values_list('pk', flat=True)),
            'managed_project_ids': list(user.managed_projects.values_list('pk', flat=True)),
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
        try:
            validate_password(p1, user=target)
        except ValidationError as e:
            for msg in e.messages:
                messages.error(request, msg)
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


class UserPrimaryGroupView(UserPageRequiredMixin, View):
    def _context(self, user, editing=False):
        return {
            'u': user,
            'all_groups': WorkGroup.objects.filter(is_active=True).order_by('sort_order', 'name'),
            'editing': editing,
        }

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        editing = request.GET.get('edit') == '1'
        return render(request, 'accounts/partials/_primary_group_cell.html', self._context(user, editing))

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        group_id = request.POST.get('group', '').strip()
        if group_id:
            user.group = get_object_or_404(WorkGroup, pk=group_id, is_active=True)
        else:
            user.group = None
        user.save(update_fields=['group'])
        return render(request, 'accounts/partials/_primary_group_cell.html', self._context(user))


class UserManagedGroupsView(AdminRequiredMixin, View):
    def _context(self, user, editing=False):
        from apps.taxonomy.models import WorkGroup
        return {
            'u': user,
            'all_groups': WorkGroup.objects.order_by('name'),
            'managed_group_ids': list(user.managed_groups.values_list('pk', flat=True)),
            'editing': editing,
        }

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        editing = request.GET.get('edit') == '1'
        return render(request, 'accounts/partials/_managed_groups_cell.html', self._context(user, editing))

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.managed_groups.set(request.POST.getlist('managed_groups'))
        return render(request, 'accounts/partials/_managed_groups_cell.html', self._context(user))


class UserManagedProjectsView(AdminRequiredMixin, View):
    def _context(self, user, editing=False):
        from apps.taxonomy.models import Project
        return {
            'u': user,
            'all_projects': Project.objects.order_by('sort_order', 'name'),
            'managed_project_ids': list(user.managed_projects.values_list('pk', flat=True)),
            'editing': editing,
        }

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        editing = request.GET.get('edit') == '1'
        return render(request, 'accounts/partials/_managed_projects_cell.html', self._context(user, editing))

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.managed_projects.set(request.POST.getlist('managed_projects'))
        return render(request, 'accounts/partials/_managed_projects_cell.html', self._context(user))


class SignupToggleView(AdminRequiredMixin, View):
    def post(self, request):
        s = SiteSettings.get_solo()
        s.allow_signup = not s.allow_signup
        s.save(update_fields=['allow_signup'])
        state = 'enabled' if s.allow_signup else 'disabled'
        messages.success(request, f'Self-serve signup {state}.')
        return redirect('admin-users')


class RolePreviewView(View):
    """Activate or exit role preview mode for admins."""

    def post(self, request):
        if not request.user.is_authenticated:
            from django.conf import settings as django_settings
            return redirect(django_settings.LOGIN_URL)

        # Re-query the DB so we check the real role even if middleware already overrode it
        real_user = User.objects.get(pk=request.user.pk)
        if real_user.role != User.Role.ADMIN:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        role = request.POST.get('role', '').strip()
        if not role or role == 'exit':
            request.session.pop('_preview_role', None)
        elif role in User.Role.values and role != User.Role.ADMIN:
            request.session['_preview_role'] = role

        return redirect(request.POST.get('next', '/'))


class GroupSelectionView(View):
    """First-login group selection — shown to authenticated users with no group set."""

    def dispatch(self, request, *args, **kwargs):
        from django.contrib.auth.mixins import LoginRequiredMixin
        if not request.user.is_authenticated:
            from django.conf import settings
            return redirect(settings.LOGIN_URL)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        groups = WorkGroup.objects.filter(is_active=True).order_by('sort_order', 'name')
        return render(request, 'accounts/select_group.html', {'groups': groups})

    def post(self, request):
        group_id = request.POST.get('group', '').strip()
        if group_id:
            try:
                group = WorkGroup.objects.get(pk=group_id, is_active=True)
                request.user.group = group
                request.user.save(update_fields=['group'])
                messages.success(request, f'Welcome! Your group has been set to "{group.name}".')
            except WorkGroup.DoesNotExist:
                messages.error(request, 'Invalid group selection.')
                return redirect('select-group')
        else:
            # User explicitly chose to skip — mark done for this session
            request.session['_group_selection_done'] = True
            messages.info(request, 'You can set your group at any time from your profile.')

        return redirect('dashboard')


class APITokenRotateView(LoginRequiredMixin, View):
    def post(self, request):
        APIToken.rotate(request.user)
        messages.success(request, 'API token generated. Copy it from your profile — it will not be shown again.')
        return redirect('profile')


class APITokenRevokeView(LoginRequiredMixin, View):
    def post(self, request):
        APIToken.objects.filter(user=request.user).delete()
        messages.success(request, 'API token revoked.')
        return redirect('profile')


class AdminCreateUserView(AdminRequiredMixin, View):
    def post(self, request):
        form = AdminCreateUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, f'User "{user.email}" created.')
            return redirect('admin-users')
        # Re-render page with form errors
        users = User.objects.order_by('email')
        return render(request, 'accounts/admin_users.html', {
            'users': users,
            'role_choices': User.Role.choices,
            'site_settings': SiteSettings.get_solo(),
            'create_form': form,
            'show_create_form': True,
        })
