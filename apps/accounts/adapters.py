from django.conf import settings

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        if getattr(settings, 'SCD_DISABLE_LOCAL_SIGNUP', False):
            return False
        from .models import SiteSettings
        return SiteSettings.get_solo().allow_signup


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        # Future CILogon: map IdP claims → user.role / user.employee_id here
        return user
