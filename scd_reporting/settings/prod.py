import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401, F403

DEBUG = False

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

_secret_key = os.environ.get('DJANGO_SECRET_KEY', '')
if not _secret_key or _secret_key.startswith('django-insecure-'):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set to a strong, unique value in production. "
        "It is missing or still set to a known development placeholder."
    )
SECRET_KEY = _secret_key
