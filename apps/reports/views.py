from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from apps.accounts.permissions import AuditorOrAdminRequiredMixin
from apps.core.markdown import render_markdown
from apps.entries.models import WorkItem

from . import ai_summary, exporters
from .filters import WorkItemFilter
from .forms import AIPromptConfigForm
from .models import AIPromptConfig

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
            'prompt_form': AIPromptConfigForm(instance=AIPromptConfig.get_solo()),
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
        _, qs = _filtered_qs(request.POST)
        selected_ids = request.POST.getlist('selected_ids')
        if selected_ids:
            qs = qs.filter(pk__in=selected_ids)
        from apps.audit.service import log_event
        log_event(
            action='export',
            request=request,
            changes={'format': fmt, 'count': qs.count(), 'selection': bool(selected_ids)},
        )
        return exporter(qs)


class ReportSummaryView(AuditorOrAdminRequiredMixin, View):
    def post(self, request):
        _, qs = _filtered_qs(request.POST)
        selected_ids = request.POST.getlist('selected_ids')
        if selected_ids:
            qs = qs.filter(pk__in=selected_ids)
        count = qs.count()
        if count == 0:
            return render(request, 'reports/partials/_summary.html', {
                'error': 'No entries matched. Adjust filters or select rows in the preview first.',
            })
        try:
            text = ai_summary.generate(qs)
        except Exception as exc:
            return render(request, 'reports/partials/_summary.html', {'error': str(exc)})
        from apps.audit.service import log_event
        log_event(
            action='export',
            request=request,
            changes={'format': 'ai_summary', 'count': count, 'selection': bool(selected_ids)},
        )
        html = render_markdown(text)
        return render(request, 'reports/partials/_summary.html', {
            'summary_text': text,
            'summary_html': html,
            'count': count,
        })


class SummaryDownloadTxtView(AuditorOrAdminRequiredMixin, View):
    def post(self, request):
        text = request.POST.get('summary_text', '')
        ts = timezone.now().strftime('%Y%m%d_%H%M')
        resp = HttpResponse(text, content_type='text/plain; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="scd_summary_{ts}.txt"'
        return resp


class SummaryDownloadPdfView(AuditorOrAdminRequiredMixin, View):
    def post(self, request):
        from ._pdf import md_to_pdf

        text = request.POST.get('summary_text', '')
        ts_label = timezone.now().strftime('%Y-%m-%d %H:%M')
        pdf_bytes = md_to_pdf(
            markdown_text=text,
            title='SCD Effort Report — AI Summary',
            meta=f'Generated {ts_label} UTC',
        )
        ts = timezone.now().strftime('%Y%m%d_%H%M')
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="scd_summary_{ts}.pdf"'
        return resp


class AIPromptConfigView(AuditorOrAdminRequiredMixin, View):
    def post(self, request):
        from django.contrib import messages
        from django.shortcuts import redirect
        if not request.user.is_scd_admin:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden()
        form = AIPromptConfigForm(request.POST, instance=AIPromptConfig.get_solo())
        if form.is_valid():
            form.save()
            messages.success(request, 'AI prompt configuration saved.')
        else:
            messages.error(request, 'Could not save — check the form for errors.')
        return redirect('reports:index')
