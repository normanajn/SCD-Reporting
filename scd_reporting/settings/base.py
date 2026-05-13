import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-dev-only-change-in-production')

DEBUG = False

ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost').split(',')]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    # Third-party
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.openid_connect',
    'allauth.socialaccount.providers.google',
    'django_htmx',
    'django_filters',
    'tailwind',
    'widget_tweaks',
    # Local
    'theme',
    'apps.core.apps.CoreConfig',
    'apps.accounts.apps.AccountsConfig',
    'apps.taxonomy.apps.TaxonomyConfig',
    'apps.entries.apps.EntriesConfig',
    'apps.reports.apps.ReportsConfig',
    'apps.audit.apps.AuditConfig',
]

AUTH_USER_MODEL = 'accounts.User'

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'apps.audit.middleware.AuditRequestMiddleware',
]

ROOT_URLCONF = 'scd_reporting.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'apps' / 'core' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.accounts.context_processors.site_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'scd_reporting.wsgi.application'

DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Chicago'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# django-allauth — local auth
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = os.environ.get('ACCOUNT_EMAIL_VERIFICATION', 'optional')
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# SSO seam — flip to '1' to disable local signup once OIDC is configured
SCD_DISABLE_LOCAL_SIGNUP = os.environ.get('SCD_DISABLE_LOCAL_SIGNUP', '0') == '1'

ACCOUNT_ADAPTER = 'apps.accounts.adapters.AccountAdapter'
SOCIALACCOUNT_ADAPTER = 'apps.accounts.adapters.SocialAccountAdapter'

# ── OIDC / SSO ────────────────────────────────────────────────────────────────
# Client secret: read from a file (preferred for production) or env var fallback.
#   OIDC_CLIENT_SECRET_FILE=/run/secrets/oidc_secret   (contents = raw secret)
#   OIDC_CLIENT_SECRET=<value>                         (direct env var fallback)
#
# Discovery URL: either the full .well-known URL or the base realm URL.
#   OIDC_PROVIDER_URL=https://host/realms/myrealm/.well-known/openid-configuration
#   OIDC_PROVIDER_URL=https://host/realms/myrealm
#
# Client ID:
#   OIDC_CLIENT_ID=scd-report-summarizer

def _read_oidc_secret():
    path = os.environ.get('OIDC_CLIENT_SECRET_FILE', '').strip()
    if path:
        try:
            return Path(path).read_text().strip()
        except OSError:
            pass
    return os.environ.get('OIDC_CLIENT_SECRET', '')

_OIDC_PROVIDER_URL = os.environ.get('OIDC_PROVIDER_URL', '').strip()
# Accept full discovery URL or base realm URL — allauth wants the base URL
_OIDC_SERVER_URL = (
    _OIDC_PROVIDER_URL.removesuffix('/.well-known/openid-configuration')
    if _OIDC_PROVIDER_URL else ''
)
OIDC_CLIENT_ID = os.environ.get('OIDC_CLIENT_ID', '').strip()
OIDC_ENABLED = bool(_OIDC_SERVER_URL and OIDC_CLIENT_ID)

# ── Google OAuth ──────────────────────────────────────────────────────────────
# GOOGLE_CLIENT_ID=<your-client-id>
# GOOGLE_CLIENT_SECRET=<your-client-secret>  (or GOOGLE_CLIENT_SECRET_FILE=<path>)

def _read_google_secret():
    path = os.environ.get('GOOGLE_CLIENT_SECRET_FILE', '').strip()
    if path:
        try:
            return Path(path).read_text().strip()
        except OSError:
            pass
    return os.environ.get('GOOGLE_CLIENT_SECRET', '')

_GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
_GOOGLE_CLIENT_SECRET = _read_google_secret()
GOOGLE_ENABLED = bool(_GOOGLE_CLIENT_ID and _GOOGLE_CLIENT_SECRET)

SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True

_SOCIALACCOUNT_PROVIDERS: dict = {}

if OIDC_ENABLED:
    _SOCIALACCOUNT_PROVIDERS['openid_connect'] = {
        'APPS': [
            {
                'provider_id': 'keycloak',
                'name': 'Fermilab SSO',
                'client_id': OIDC_CLIENT_ID,
                'secret': _read_oidc_secret(),
                'settings': {
                    'server_url': _OIDC_SERVER_URL,
                },
            }
        ]
    }

if GOOGLE_ENABLED:
    _SOCIALACCOUNT_PROVIDERS['google'] = {
        'APPS': [
            {
                'provider_id': 'google',
                'name': 'Google',
                'client_id': _GOOGLE_CLIENT_ID,
                'secret': _GOOGLE_CLIENT_SECRET,
                'settings': {
                    'scope': ['profile', 'email'],
                    'auth_params': {'access_type': 'online'},
                },
            }
        ]
    }

if _SOCIALACCOUNT_PROVIDERS:
    SOCIALACCOUNT_PROVIDERS = _SOCIALACCOUNT_PROVIDERS

TAILWIND_APP_NAME = 'theme'
INTERNAL_IPS = ['127.0.0.1']

# Anthropic — used for AI report summaries
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
ANTHROPIC_SUMMARY_MODEL = os.environ.get('ANTHROPIC_SUMMARY_MODEL', 'claude-sonnet-4-6')
