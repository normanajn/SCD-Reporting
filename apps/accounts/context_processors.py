from .models import SiteSettings


def site_settings(request):
    settings = SiteSettings.get_solo()
    return {'ACCOUNT_ALLOW_SIGNUPS': settings.allow_signup}
