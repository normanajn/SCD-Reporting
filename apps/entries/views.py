from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Q
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.accounts.permissions import EntryManagerRequiredMixin
from apps.core.markdown import render_markdown
from apps.taxonomy.models import Project, Tag

from .forms import WorkItemForm
from .models import WorkItem


# ── List ──────────────────────────────────────────────────────────────────────

class EntryListView(LoginRequiredMixin, ListView):
    model = WorkItem
    template_name = 'entries/list.html'
    context_object_name = 'entries'
    paginate_by = 25

    def get_queryset(self):
        qs = (WorkItem.objects
              .filter(author=self.request.user, is_archived=False)
              .select_related('project', 'category')
              .prefetch_related('tags'))
        project_id = self.request.GET.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['projects'] = Project.objects.filter(is_active=True).order_by('sort_order', 'name')
        ctx['selected_project'] = self.request.GET.get('project', '')
        return ctx


# ── Create ────────────────────────────────────────────────────────────────────

class EntryCreateView(LoginRequiredMixin, CreateView):
    model = WorkItem
    form_class = WorkItemForm
    template_name = 'entries/form.html'

    def get_initial(self):
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        initial = {
            'period_kind':  'week',
            'period_start': week_start.isoformat(),
            'period_end':   (week_start + timedelta(days=6)).isoformat(),
        }
        if self.request.user.group_id:
            initial['group'] = self.request.user.group_id
        prefill_desc = self.request.session.pop('prefill_description', None)
        if prefill_desc is not None:
            initial['description'] = prefill_desc
            initial.setdefault('title', 'AI Summary')
        return initial

    def form_valid(self, form):
        form.instance.author = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Entry "{self.object.title}" submitted.')
        return response

    def get_success_url(self):
        return reverse('entries:detail', kwargs={'pk': self.object.pk})


# ── Detail ────────────────────────────────────────────────────────────────────

class EntryDetailView(LoginRequiredMixin, DetailView):
    model = WorkItem
    template_name = 'entries/detail.html'

    def get_queryset(self):
        qs = WorkItem.objects.prefetch_related('tags')
        user = self.request.user
        if user.is_scd_admin or user.is_division_head:
            pass  # full access including division-head-only entries
        elif user.is_auditor:
            qs = qs.filter(Q(is_division_head_only=False) | Q(author=user))
        else:
            qs = qs.filter(author=user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['description_html'] = render_markdown(self.object.description)
        return ctx


# ── Edit ──────────────────────────────────────────────────────────────────────

class EntryUpdateView(LoginRequiredMixin, UpdateView):
    model = WorkItem
    form_class = WorkItemForm
    template_name = 'entries/form.html'

    def get_queryset(self):
        return WorkItem.objects.filter(author=self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Entry updated.')
        return response

    def get_success_url(self):
        return reverse('entries:detail', kwargs={'pk': self.object.pk})


# ── Delete ────────────────────────────────────────────────────────────────────

class EntryDeleteView(LoginRequiredMixin, DeleteView):
    model = WorkItem
    template_name = 'entries/confirm_delete.html'
    success_url = reverse_lazy('entries:list')

    def get_queryset(self):
        return WorkItem.objects.filter(author=self.request.user)

    def form_valid(self, form):
        tag_ids = list(self.object.tags.values_list('id', flat=True))
        title = self.object.title
        response = super().form_valid(form)
        if tag_ids:
            Tag.objects.filter(id__in=tag_ids).update(use_count=F('use_count') - 1)
        messages.success(self.request, f'Entry "{title}" deleted.')
        return response


# ── Create from AI summary ────────────────────────────────────────────────────

class EntryCreateFromSummaryView(LoginRequiredMixin, View):
    def post(self, request):
        request.session['prefill_description'] = request.POST.get('summary_text', '')
        return redirect(reverse('entries:create'))


# ── HTMX: period prefill ──────────────────────────────────────────────────────

class PeriodPrefillView(LoginRequiredMixin, View):
    def get(self, request):
        kind  = request.GET.get('kind', 'week')
        today = date.today()
        if kind == 'today':
            start = end = today
        elif kind == 'week':
            start = today - timedelta(days=today.weekday())
            end   = start + timedelta(days=6)
        elif kind == 'fortnight':
            start = today - timedelta(days=13)
            end   = today
        elif kind == 'month':
            start = today.replace(day=1)
            end   = today
        else:
            start = end = today
        return render(request, 'entries/partials/_period_inputs.html', {
            'period_start': start.isoformat(),
            'period_end':   end.isoformat(),
        })


# ── HTMX: markdown preview ────────────────────────────────────────────────────

class MarkdownPreviewView(LoginRequiredMixin, View):
    def post(self, request):
        text = request.POST.get('description', '')
        return render(request, 'entries/partials/_markdown_preview.html', {
            'html': render_markdown(text),
        })


# ── Entry management (admin / division head / group leader) ───────────────────

class EntryManageView(EntryManagerRequiredMixin, ListView):
    model = WorkItem
    template_name = 'entries/manage.html'
    context_object_name = 'entries'
    paginate_by = 50

    def get_queryset(self):
        from apps.accounts.models import User
        qs = (WorkItem.objects
              .select_related('author', 'project', 'category')
              .prefetch_related('tags'))
        user = self.request.user
        if not (user.is_scd_admin or user.is_division_head):
            qs = qs.filter(is_division_head_only=False)
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(title__icontains=q)
        author = self.request.GET.get('author', '').strip()
        if author:
            qs = qs.filter(author__email__icontains=author)
        project = self.request.GET.get('project', '').strip()
        if project:
            qs = qs.filter(project_id=project)
        show_archived = self.request.GET.get('archived') == '1'
        if show_archived:
            qs = qs.filter(is_archived=True)
        else:
            qs = qs.filter(is_archived=False)
        return qs.order_by('-period_end', 'author__email')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['projects'] = Project.objects.filter(is_active=True).order_by('sort_order', 'name')
        ctx['show_archived'] = self.request.GET.get('archived') == '1'
        from apps.accounts.models import User
        ctx['all_users'] = User.objects.order_by('email')
        return ctx


class EntryReassignView(EntryManagerRequiredMixin, View):
    def post(self, request, pk):
        from apps.accounts.models import User
        entry = WorkItem.objects.get(pk=pk)
        new_author_id = request.POST.get('author_id')
        try:
            new_author = User.objects.get(pk=new_author_id)
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('entries:manage')
        old_email = entry.author.email
        entry.author = new_author
        entry.save(update_fields=['author', 'updated_at'])
        messages.success(request, f'Entry "{entry.title}" reassigned from {old_email} to {new_author.email}.')
        return redirect(request.POST.get('next', reverse('entries:manage')))


class EntryArchiveView(EntryManagerRequiredMixin, View):
    def post(self, request, pk):
        entry = WorkItem.objects.get(pk=pk)
        entry.is_archived = not entry.is_archived
        entry.save(update_fields=['is_archived', 'updated_at'])
        action = 'archived' if entry.is_archived else 'unarchived'
        messages.success(request, f'Entry "{entry.title}" {action}.')
        return redirect(request.POST.get('next', reverse('entries:manage')))


class EntryManagerDeleteView(EntryManagerRequiredMixin, View):
    def post(self, request, pk):
        entry = WorkItem.objects.get(pk=pk)
        tag_ids = list(entry.tags.values_list('id', flat=True))
        title = entry.title
        entry.delete()
        if tag_ids:
            Tag.objects.filter(id__in=tag_ids).update(use_count=F('use_count') - 1)
        messages.success(request, f'Entry "{title}" permanently deleted.')
        return redirect(request.POST.get('next', reverse('entries:manage')))
