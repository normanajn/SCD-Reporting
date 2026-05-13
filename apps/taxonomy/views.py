import json
from datetime import datetime, timezone

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import UpdateView

from apps.accounts.permissions import AdminRequiredMixin

from .forms import CategoryForm, ProjectForm, WorkGroupForm
from .models import Category, Project, Tag, WorkGroup


class ProjectManageView(AdminRequiredMixin, View):
    template_name = 'taxonomy/projects.html'

    def _ctx(self, form=None):
        return {
            'projects': Project.objects.order_by('sort_order', 'name'),
            'form': form or ProjectForm(),
        }

    def get(self, request):
        return render(request, self.template_name, self._ctx())

    def post(self, request):
        form = ProjectForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f'Project "{obj.name}" added.')
            return redirect('taxonomy:projects')
        return render(request, self.template_name, self._ctx(form))


class ProjectEditView(AdminRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'taxonomy/project_form.html'
    success_url = reverse_lazy('taxonomy:projects')

    def form_valid(self, form):
        messages.success(self.request, f'Project "{form.instance.name}" saved.')
        return super().form_valid(form)


class CategoryManageView(AdminRequiredMixin, View):
    template_name = 'taxonomy/categories.html'

    def _ctx(self, form=None):
        return {
            'categories': Category.objects.order_by('sort_order', 'name'),
            'form': form or CategoryForm(),
        }

    def get(self, request):
        return render(request, self.template_name, self._ctx())

    def post(self, request):
        form = CategoryForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f'Category "{obj.name}" added.')
            return redirect('taxonomy:categories')
        return render(request, self.template_name, self._ctx(form))


class CategoryEditView(AdminRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'taxonomy/category_form.html'
    success_url = reverse_lazy('taxonomy:categories')

    def form_valid(self, form):
        messages.success(self.request, f'Category "{form.instance.name}" saved.')
        return super().form_valid(form)


class WorkGroupManageView(AdminRequiredMixin, View):
    template_name = 'taxonomy/groups.html'

    def _ctx(self, form=None):
        return {
            'groups': WorkGroup.objects.order_by('sort_order', 'name'),
            'form': form or WorkGroupForm(),
        }

    def get(self, request):
        return render(request, self.template_name, self._ctx())

    def post(self, request):
        form = WorkGroupForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f'Group "{obj.name}" added.')
            return redirect('taxonomy:groups')
        return render(request, self.template_name, self._ctx(form))


class WorkGroupEditView(AdminRequiredMixin, UpdateView):
    model = WorkGroup
    form_class = WorkGroupForm
    template_name = 'taxonomy/group_form.html'
    success_url = reverse_lazy('taxonomy:groups')

    def form_valid(self, form):
        messages.success(self.request, f'Group "{form.instance.name}" saved.')
        return super().form_valid(form)


class TaxonomyExportView(AdminRequiredMixin, View):
    def get(self, request):
        def rows(qs):
            return [
                {
                    'name':       obj.name,
                    'slug':       obj.slug,
                    'short_code': obj.short_code,
                    'is_active':  obj.is_active,
                    'sort_order': obj.sort_order,
                }
                for obj in qs
            ]

        payload = {
            'exported_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'projects':    rows(Project.objects.order_by('sort_order', 'name')),
            'categories':  rows(Category.objects.order_by('sort_order', 'name')),
            'groups':      rows(WorkGroup.objects.order_by('sort_order', 'name')),
        }
        filename = f"taxonomy-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
        response = HttpResponse(
            json.dumps(payload, indent=2),
            content_type='application/json',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class TaxonomyImportView(AdminRequiredMixin, View):
    TABLES = {
        'projects':   Project,
        'categories': Category,
        'groups':     WorkGroup,
    }
    FIELDS = ('name', 'short_code', 'is_active', 'sort_order')

    def post(self, request):
        upload = request.FILES.get('taxonomy_file')
        if not upload:
            messages.error(request, 'No file selected.')
            return redirect('taxonomy:projects')

        try:
            data = json.loads(upload.read().decode('utf-8'))
        except (ValueError, UnicodeDecodeError) as e:
            messages.error(request, f'Invalid JSON file: {e}')
            return redirect('taxonomy:projects')

        if not isinstance(data, dict) or not any(k in data for k in self.TABLES):
            messages.error(request, 'File does not look like a taxonomy export.')
            return redirect('taxonomy:projects')

        totals = {}
        for key, model in self.TABLES.items():
            records = data.get(key, [])
            created = updated = 0
            for rec in records:
                slug = rec.get('slug', '').strip()
                name = rec.get('name', '').strip()
                if not slug and not name:
                    continue
                defaults = {f: rec[f] for f in self.FIELDS if f in rec}
                if slug:
                    obj, is_new = model.objects.update_or_create(slug=slug, defaults=defaults)
                else:
                    obj, is_new = model.objects.update_or_create(name=name, defaults=defaults)
                if is_new:
                    created += 1
                else:
                    updated += 1
            totals[key] = (created, updated)

        parts = [
            f"{key}: {c} created, {u} updated"
            for key, (c, u) in totals.items()
        ]
        messages.success(request, 'Taxonomy restored — ' + '; '.join(parts) + '.')
        return redirect('taxonomy:projects')


class TagAutocompleteView(LoginRequiredMixin, View):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        if not q:
            return HttpResponse('')
        tags = Tag.objects.filter(name__icontains=q.lower()).order_by('-use_count', 'name')[:10]
        return render(request, 'taxonomy/partials/_tag_results.html', {'tags': tags, 'q': q})
