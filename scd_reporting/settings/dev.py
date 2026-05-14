from .base import *  # noqa: F401, F403

DEBUG = True

SECRET_KEY = 'django-insecure-dev-only-do-not-use-in-production-abc123xyz789'

ALLOWED_HOSTS = ['*']

# Always log emails to console in dev, regardless of EMAIL_HOST
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
