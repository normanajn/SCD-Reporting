from django.conf import settings as django_settings

from .models import SiteSettings


def site_settings(request):
    s = SiteSettings.get_solo()
    return {
        'ACCOUNT_ALLOW_SIGNUPS': s.allow_signup,
        'OIDC_ENABLED': getattr(django_settings, 'OIDC_ENABLED', False),
    }
