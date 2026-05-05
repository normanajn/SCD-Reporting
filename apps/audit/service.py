"""Central audit logging service. All callers go through log_event()."""
from __future__ import annotations


def _get_ip(request) -> str | None:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or None


def log_event(
    *,
    action: str,
    actor=None,
    obj=None,
    changes: dict | None = None,
    request=None,
) -> None:
    from .middleware import get_current_request
    from .models import AuditLogEntry

    req = request or get_current_request()

    ip_address = None
    user_agent = ''
    if req is not None:
        ip_address = _get_ip(req)
        user_agent = req.META.get('HTTP_USER_AGENT', '')[:500]
        if actor is None and hasattr(req, 'user') and req.user.is_authenticated:
            actor = req.user

    AuditLogEntry.objects.create(
        actor=actor,
        action=action,
        object_type=type(obj).__name__ if obj is not None else '',
        object_id=obj.pk if obj is not None and obj.pk else None,
        object_repr=str(obj)[:200] if obj is not None else '',
        changes=changes or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
