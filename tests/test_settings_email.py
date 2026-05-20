import importlib
import os
import sys
from unittest.mock import patch

import pytest


_BASE_ENV_KEYS = {
    'EMAIL_HOST': '',
    'EMAIL_HOST_USER': '',
    'EMAIL_HOST_PASSWORD': '',
    'SMTP_DEBUG': '',
    'OIDC_PROVIDER_URL': '',
    'OIDC_CLIENT_ID': '',
    'OIDC_CLIENT_SECRET': '',
    'OIDC_CLIENT_SECRET_FILE': '',
    'GOOGLE_CLIENT_ID': '',
    'GOOGLE_CLIENT_SECRET': '',
    'GOOGLE_CLIENT_SECRET_FILE': '',
}


def _reload_base(overrides=None):
    env = {**_BASE_ENV_KEYS, **(overrides or {})}
    for key in list(sys.modules):
        if key.startswith('scd_reporting.settings'):
            del sys.modules[key]
    with patch.dict(os.environ, env):
        return importlib.import_module('scd_reporting.settings.base')


class TestEmailBackendSelection:
    def test_no_email_host_uses_console_backend(self):
        mod = _reload_base({})
        assert mod.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend'

    def test_email_host_uses_logging_backend_by_default(self):
        mod = _reload_base({'EMAIL_HOST': 'smtp.example.com'})
        assert mod.EMAIL_BACKEND == 'apps.core.mail.LoggingEmailBackend'

    def test_smtp_debug_flag_enables_debug_backend(self):
        mod = _reload_base({'EMAIL_HOST': 'smtp.example.com', 'SMTP_DEBUG': '1'})
        assert mod.EMAIL_BACKEND == 'apps.core.mail.DebugEmailBackend'

    def test_smtp_debug_zero_uses_logging_backend(self):
        mod = _reload_base({'EMAIL_HOST': 'smtp.example.com', 'SMTP_DEBUG': '0'})
        assert mod.EMAIL_BACKEND == 'apps.core.mail.LoggingEmailBackend'

    def test_smtp_debug_without_email_host_has_no_effect(self):
        mod = _reload_base({'SMTP_DEBUG': '1'})
        assert mod.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend'


class TestEmailLoggerLevel:
    def test_mail_logger_defaults_to_info(self):
        mod = _reload_base({'EMAIL_HOST': 'smtp.example.com'})
        level = mod.LOGGING['loggers']['django.core.mail']['level']
        assert level == 'INFO'

    def test_debug_backend_still_uses_info_logger_level(self):
        mod = _reload_base({'EMAIL_HOST': 'smtp.example.com', 'SMTP_DEBUG': '1'})
        level = mod.LOGGING['loggers']['django.core.mail']['level']
        assert level == 'INFO'
