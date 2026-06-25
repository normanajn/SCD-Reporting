"""Auto-log WorkItem changes and auth events via Django signals."""
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.entries.models import WorkItem

from .service import log_event

_TRACKED_FIELDS = (
    'title', 'entry_type_id', 'group_id',
    'period_kind', 'period_start', 'period_end',
    'description', 'is_private', 'is_critical', 'is_highlight', 'highlight_stars',
    'is_division_head_only', 'author_id', 'is_archived',
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

def _resolve_author_email(author_id):
    from apps.accounts.models import User as _User
    try:
        return _User.objects.get(pk=author_id).email
    except (_User.DoesNotExist, TypeError, ValueError):
        return str(author_id)


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
        # Make author changes readable — replace raw FK ids with email addresses
        if 'author_id' in changes:
            changes['author_id'] = {
                'old': _resolve_author_email(old.get('author_id')),
                'new': _resolve_author_email(getattr(instance, 'author_id')),
            }
        if changes:
            log_event(action='update', obj=instance, changes=changes)


# ── WorkItem post_delete: log delete ─────────────────────────────────────────

@receiver(post_delete, sender=WorkItem)
def _workitem_deleted(sender, instance, **kwargs):
    log_event(action='delete', obj=instance)


# ── WorkItem tag m2m changes ──────────────────────────────────────────────────

@receiver(m2m_changed, sender=WorkItem.tags.through)
def _workitem_tags_changed(sender, instance, action, pk_set, **kwargs):
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return
    if not isinstance(instance, WorkItem):
        return  # guard: m2m_changed fires for both sides of the relation

    from apps.taxonomy.models import Tag

    if action == 'post_add' and pk_set:
        names = sorted(Tag.objects.filter(pk__in=pk_set).values_list('name', flat=True))
        if names:
            log_event(action='update', obj=instance, changes={'tags_added': names})
    elif action == 'post_remove' and pk_set:
        names = sorted(Tag.objects.filter(pk__in=pk_set).values_list('name', flat=True))
        if names:
            log_event(action='update', obj=instance, changes={'tags_removed': names})
    elif action == 'post_clear':
        log_event(action='update', obj=instance, changes={'tags_cleared': True})


# ── WorkItem taxonomy m2m changes (projects / categories / lab priorities) ────

def _log_taxonomy_m2m(instance, action, pk_set, model, label):
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return
    if not isinstance(instance, WorkItem):
        return  # guard: m2m_changed fires for both sides of the relation
    if action == 'post_add' and pk_set:
        names = sorted(model.objects.filter(pk__in=pk_set).values_list('name', flat=True))
        if names:
            log_event(action='update', obj=instance, changes={f'{label}_added': names})
    elif action == 'post_remove' and pk_set:
        names = sorted(model.objects.filter(pk__in=pk_set).values_list('name', flat=True))
        if names:
            log_event(action='update', obj=instance, changes={f'{label}_removed': names})
    elif action == 'post_clear':
        log_event(action='update', obj=instance, changes={f'{label}_cleared': True})


@receiver(m2m_changed, sender=WorkItem.projects.through)
def _workitem_projects_changed(sender, instance, action, pk_set, **kwargs):
    from apps.taxonomy.models import Project
    _log_taxonomy_m2m(instance, action, pk_set, Project, 'projects')


@receiver(m2m_changed, sender=WorkItem.categories.through)
def _workitem_categories_changed(sender, instance, action, pk_set, **kwargs):
    from apps.taxonomy.models import Category
    _log_taxonomy_m2m(instance, action, pk_set, Category, 'categories')


@receiver(m2m_changed, sender=WorkItem.lab_priorities.through)
def _workitem_lab_priorities_changed(sender, instance, action, pk_set, **kwargs):
    from apps.taxonomy.models import LabPriority
    _log_taxonomy_m2m(instance, action, pk_set, LabPriority, 'lab_priorities')


# ── Auth events ───────────────────────────────────────────────────────────────

@receiver(user_logged_in)
def _user_logged_in(sender, request, user, **kwargs):
    log_event(action='login', actor=user, request=request)


@receiver(user_logged_out)
def _user_logged_out(sender, request, user, **kwargs):
    log_event(action='logout', actor=user, request=request)
