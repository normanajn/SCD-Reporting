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

        # Map standard OIDC claims from the IdP (Keycloak / CILogon compatible)
        extra = sociallogin.account.extra_data

        # Display name: prefer full name, fall back to preferred_username
        display_name = (
            extra.get('name')
            or f"{extra.get('given_name', '')} {extra.get('family_name', '')}".strip()
            or extra.get('preferred_username', '')
        )
        if display_name:
            user.display_name = display_name

        # Employee ID: some IdPs expose this as employee_number or employeeNumber
        employee_id = (
            extra.get('employee_number')
            or extra.get('employeeNumber')
            or extra.get('employee_id')
            or ''
        )
        if employee_id:
            user.employee_id = str(employee_id)

        return user
