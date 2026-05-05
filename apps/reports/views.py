from django.shortcuts import render
from django.views import View

from apps.accounts.permissions import AuditorOrAdminRequiredMixin
from apps.entries.models import WorkItem

from . import exporters
from .filters import WorkItemFilter

PREVIEW_LIMIT = 50


def _filtered_qs(data):
    qs = WorkItem.objects.select_related('author', 'project', 'category').prefetch_related('tags')
    f = WorkItemFilter(data, queryset=qs)
    return f, f.qs.order_by('-period_end', 'author__email')


class ReportIndexView(AuditorOrAdminRequiredMixin, View):
    def get(self, request):
        f = WorkItemFilter(queryset=WorkItem.objects.none())
        return render(request, 'reports/index.html', {
            'filter': f,
            'formats': exporters.available(),
        })


class ReportPreviewView(AuditorOrAdminRequiredMixin, View):
    def post(self, request):
        f, qs = _filtered_qs(request.POST)
        total = qs.count()
        rows  = qs[:PREVIEW_LIMIT]
        return render(request, 'reports/partials/_preview.html', {
            'filter':  f,
            'rows':    rows,
            'total':   total,
            'limit':   PREVIEW_LIMIT,
        })


class ReportDownloadView(AuditorOrAdminRequiredMixin, View):
    def post(self, request, fmt: str):
        exporter = exporters.get(fmt)
        if not exporter:
            from django.http import HttpResponseBadRequest
            return HttpResponseBadRequest(f'Unknown format: {fmt}')
        f, qs = _filtered_qs(request.POST)
        from apps.audit.service import log_event
        log_event(
            action='export',
            request=request,
            changes={'format': fmt, 'count': qs.count()},
        )
        return exporter(qs)
