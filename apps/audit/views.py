from django.views.generic import ListView

from apps.accounts.permissions import AuditorOrAdminRequiredMixin

from .models import AuditLogEntry

PAGE_SIZE = 50


class AuditLogView(AuditorOrAdminRequiredMixin, ListView):
    model = AuditLogEntry
    template_name = 'audit/index.html'
    context_object_name = 'entries'
    paginate_by = PAGE_SIZE

    def get_queryset(self):
        qs = AuditLogEntry.objects.select_related('actor')

        q = self.request.GET
        if q.get('actor'):
            qs = qs.filter(actor__email__icontains=q['actor'])
        if q.get('action'):
            qs = qs.filter(action=q['action'])
        if q.get('object_type'):
            qs = qs.filter(object_type=q['object_type'])
        if q.get('date_after'):
            qs = qs.filter(timestamp__date__gte=q['date_after'])
        if q.get('date_before'):
            qs = qs.filter(timestamp__date__lte=q['date_before'])
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['action_choices'] = AuditLogEntry.Action.choices
        ctx['object_types']   = (
            AuditLogEntry.objects
            .exclude(object_type='')
            .values_list('object_type', flat=True)
            .distinct()
            .order_by('object_type')
        )
        ctx['q'] = self.request.GET
        return ctx
