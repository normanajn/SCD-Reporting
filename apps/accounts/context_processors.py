from django.conf import settings as django_settings

from .models import SiteSettings


def site_settings(request):
    s = SiteSettings.get_solo()
    from allauth.mfa import app_settings as mfa_settings
    return {
        'ACCOUNT_ALLOW_SIGNUPS': s.allow_signup,
        'OIDC_ENABLED': getattr(django_settings, 'OIDC_ENABLED', False),
        'GOOGLE_ENABLED': getattr(django_settings, 'GOOGLE_ENABLED', False),
        'PASSKEY_LOGIN_ENABLED': mfa_settings.PASSKEY_LOGIN_ENABLED,
    }
