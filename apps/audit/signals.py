"""Auto-log WorkItem changes and auth events via Django signals."""
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.entries.models import WorkItem

from .service import log_event

_TRACKED_FIELDS = (
    'title', 'project_id', 'category_id', 'group_id',
    'period_kind', 'period_start', 'period_end',
    'description', 'is_private', 'is_critical', 'is_highlight', 'highlight_stars',
)


# ── WorkItem pre_save: snapshot old values ────────────────────────────────────

@receiver(pre_save, sender=WorkItem)
def _workitem_snapshot(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = WorkItem.objects.get(pk=instance.pk)
            instance._audit_old = {
                f: str(getattr(old, f)) for f in _TRACKED_FIELDS
            }
        except WorkItem.DoesNotExist:
            instance._audit_old = {}
    else:
        instance._audit_old = {}


# ── WorkItem post_save: log create / update ───────────────────────────────────

@receiver(post_save, sender=WorkItem)
def _workitem_saved(sender, instance, created, **kwargs):
    if created:
        log_event(action='create', obj=instance)
    else:
        old = getattr(instance, '_audit_old', {})
        changes = {}
        for f in _TRACKED_FIELDS:
            new_val = str(getattr(instance, f))
            if old.get(f) != new_val:
                changes[f] = {'old': old.get(f), 'new': new_val}
        if changes:
            log_event(action='update', obj=instance, changes=changes)


# ── WorkItem post_delete: log delete ─────────────────────────────────────────

@receiver(post_delete, sender=WorkItem)
def _workitem_deleted(sender, instance, **kwargs):
    log_event(action='delete', obj=instance)


# ── Auth events ───────────────────────────────────────────────────────────────

@receiver(user_logged_in)
def _user_logged_in(sender, request, user, **kwargs):
    log_event(action='login', actor=user, request=request)


@receiver(user_logged_out)
def _user_logged_out(sender, request, user, **kwargs):
    log_event(action='logout', actor=user, request=request)
