import subprocess

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from .markdown import render_markdown


def _git_info():
    try:
        commit = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'], stderr=subprocess.DEVNULL
        ).decode().strip()
        date = subprocess.check_output(
            ['git', 'log', '-1', '--format=%ad', '--date=short'], stderr=subprocess.DEVNULL
        ).decode().strip()
        try:
            tag = subprocess.check_output(
                ['git', 'describe', '--tags', '--exact-match', 'HEAD'], stderr=subprocess.DEVNULL
            ).decode().strip()
        except subprocess.CalledProcessError:
            tag = ''
        return {'commit': commit, 'date': date, 'tag': tag}
    except Exception:
        return {'commit': 'unknown', 'date': 'unknown', 'tag': ''}


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.entries.models import WorkItem
        from apps.reports.forms import AIPromptConfigForm
        from apps.reports.models import AIPromptConfig
        ctx['recent_entries'] = (
            WorkItem.objects
            .filter(author=self.request.user)
            .select_related('project', 'category')
            .prefetch_related('tags')
            .order_by('-period_end', '-created_at')[:20]
        )
        ctx['prompt_form'] = AIPromptConfigForm(instance=AIPromptConfig.for_user(self.request.user))
        return ctx


class DashboardSummaryView(LoginRequiredMixin, View):
    def post(self, request):
        from apps.entries.models import WorkItem
        from apps.reports.ai_summary import generate

        selected_ids = request.POST.getlist('selected_ids')
        if not selected_ids:
            return render(request, 'core/partials/_dashboard_summary.html', {
                'error': 'Select at least one entry to summarize.',
            })
        qs = (WorkItem.objects
              .filter(author=request.user, pk__in=selected_ids)
              .select_related('author', 'project', 'category')
              .prefetch_related('tags'))
        count = qs.count()
        if count == 0:
            return render(request, 'core/partials/_dashboard_summary.html', {
                'error': 'No matching entries found.',
            })
        try:
            text = generate(qs, user=request.user)
        except Exception as exc:
            return render(request, 'core/partials/_dashboard_summary.html', {'error': str(exc)})
        return render(request, 'core/partials/_dashboard_summary.html', {
            'summary_text': text,
            'summary_html': render_markdown(text),
            'count': count,
        })


class DashboardSummaryDownloadTxtView(LoginRequiredMixin, View):
    def post(self, request):
        text = request.POST.get('summary_text', '')
        ts = timezone.now().strftime('%Y%m%d_%H%M')
        resp = HttpResponse(text, content_type='text/plain; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="my_summary_{ts}.txt"'
        return resp


class DashboardSummaryDownloadMdView(LoginRequiredMixin, View):
    def post(self, request):
        text = request.POST.get('summary_text', '')
        ts = timezone.now().strftime('%Y%m%d_%H%M')
        resp = HttpResponse(text, content_type='text/markdown; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="my_summary_{ts}.md"'
        return resp


class DashboardSummaryDownloadPdfView(LoginRequiredMixin, View):
    def post(self, request):
        from apps.reports._pdf import md_to_pdf
        text = request.POST.get('summary_text', '')
        ts_label = timezone.now().strftime('%Y-%m-%d %H:%M')
        pdf_bytes = md_to_pdf(
            markdown_text=text,
            title='SCD Activity Summary',
            meta=f'Generated {ts_label} UTC',
        )
        ts = timezone.now().strftime('%Y%m%d_%H%M')
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="my_summary_{ts}.pdf"'
        return resp


class DashboardPromptConfigView(LoginRequiredMixin, View):
    def post(self, request):
        from apps.reports.forms import AIPromptConfigForm
        from apps.reports.models import AIPromptConfig
        form = AIPromptConfigForm(request.POST, instance=AIPromptConfig.get_or_create_for_user(request.user))
        if form.is_valid():
            form.save()
            messages.success(request, 'AI prompt configuration saved.')
        else:
            messages.error(request, 'Could not save — check the form for errors.')
        return redirect('dashboard')


class AboutView(LoginRequiredMixin, TemplateView):
    template_name = 'core/about.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['git'] = _git_info()
        return ctx


class BugReportView(LoginRequiredMixin, TemplateView):
    template_name = 'core/bug_report.html'


class BugReportSubmitView(LoginRequiredMixin, View):
    REPO = 'normanajn/SCD-Reporting'

    def post(self, request):
        import urllib.parse

        import requests as http_requests
        from django.conf import settings as django_settings

        title = request.POST.get('title', '').strip()
        body = request.POST.get('body', '').strip()
        if not title or not body:
            messages.error(request, 'Title and description are required.')
            return redirect('bug-report')

        reporter = request.user.display_name or request.user.email
        git = _git_info()
        full_body = (
            f"{body}\n\n"
            f"---\n"
            f"**Reported by:** {reporter}  \n"
            f"**Build:** {git['commit']} ({git['date']})"
        )

        token = getattr(django_settings, 'GITHUB_TOKEN', '') or os.environ.get('GITHUB_TOKEN', '')
        if token:
            try:
                resp = http_requests.post(
                    f'https://api.github.com/repos/{self.REPO}/issues',
                    json={'title': title, 'body': full_body, 'labels': ['bug']},
                    headers={
                        'Authorization': f'Bearer {token}',
                        'Accept': 'application/vnd.github+json',
                        'X-GitHub-Api-Version': '2022-11-28',
                    },
                    timeout=15,
                )
                if resp.status_code == 201:
                    issue_url = resp.json().get('html_url', '')
                    messages.success(request, f'Bug report submitted. {issue_url}')
                else:
                    messages.error(request, f'GitHub error {resp.status_code}: {resp.json().get("message", "")}')
            except Exception as exc:
                messages.error(request, f'Could not submit issue: {exc}')
        else:
            # No token — give the user a pre-filled GitHub URL to open manually
            params = urllib.parse.urlencode({'title': title, 'body': full_body, 'labels': 'bug'})
            gh_url = f'https://github.com/{self.REPO}/issues/new?{params}'
            messages.warning(
                request,
                f'GitHub token not configured. Open this URL to file the issue manually: {gh_url}',
            )

        return redirect('about')
