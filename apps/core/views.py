from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.entries.models import WorkItem
        ctx['recent_entries'] = (
            WorkItem.objects
            .filter(author=self.request.user)
            .select_related('project', 'category')
            .prefetch_related('tags')[:5]
        )
        return ctx
