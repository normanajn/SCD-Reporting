from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

_SELECT_GROUP_URL = None  # resolved lazily to avoid AppRegistryNotReady


def _select_group_url():
    global _SELECT_GROUP_URL
    if _SELECT_GROUP_URL is None:
        _SELECT_GROUP_URL = reverse('select-group')
    return _SELECT_GROUP_URL


# Paths that must always be reachable regardless of group status
_PASSTHROUGH_PREFIXES = (
    '/accounts/',   # allauth login/logout/SSO callbacks
    '/static/',
    '/media/',
    '/__debug__/',
)


class GroupSelectionMiddleware:
    """Redirect authenticated users without a group to the group selection page."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and not request.user.group_id
            and not request.session.get('_group_selection_done')
            and not self._is_passthrough(request.path)
            and request.path != _select_group_url()
        ):
            from apps.taxonomy.models import WorkGroup
            if WorkGroup.objects.filter(is_active=True).exists():
                return redirect(_select_group_url())

        return self.get_response(request)

    @staticmethod
    def _is_passthrough(path):
        return any(path.startswith(p) for p in _PASSTHROUGH_PREFIXES)
