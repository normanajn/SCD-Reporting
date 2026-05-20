from .base import *  # noqa: F401, F403

DEBUG = True

MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN = True

SECRET_KEY = 'django-insecure-dev-only-do-not-use-in-production-abc123xyz789'

ALLOWED_HOSTS = ['*']

# Always log emails to console in dev, regardless of EMAIL_HOST
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

SESSION_COOKIE_SAMESITE = 'Lax'

# File-based sessions avoid the UpdateError / SessionInterrupted that the
# database backend can produce when allauth's OIDC callback cycles the session
# key (deletes old DB row, inserts new one) and Django 5's session middleware
# then tries to save the now-gone original key a second time.
SESSION_ENGINE = 'django.contrib.sessions.backends.file'
