import importlib
import os
import sys
from unittest.mock import patch

import pytest
from django.core.exceptions import ImproperlyConfigured


def _reload_prod(overrides=None):
    """Re-import scd_reporting.settings.prod with a controlled environment."""
    env = {**(overrides or {})}
    for key in list(sys.modules):
        if key.startswith('scd_reporting.settings'):
            del sys.modules[key]
    with patch.dict(os.environ, env, clear=True):
        return importlib.import_module('scd_reporting.settings.prod')


class TestProdSecretKey:
    def test_fails_when_secret_key_missing(self):
        with pytest.raises(ImproperlyConfigured, match='DJANGO_SECRET_KEY'):
            _reload_prod({})

    def test_fails_when_secret_key_is_dev_placeholder(self):
        with pytest.raises(ImproperlyConfigured, match='DJANGO_SECRET_KEY'):
            _reload_prod({'DJANGO_SECRET_KEY': 'django-insecure-dev-only-change-in-production'})

    def test_fails_when_any_insecure_prefixed_key(self):
        with pytest.raises(ImproperlyConfigured, match='DJANGO_SECRET_KEY'):
            _reload_prod({'DJANGO_SECRET_KEY': 'django-insecure-some-other-value'})

    def test_succeeds_with_valid_secret_key(self):
        mod = _reload_prod({'DJANGO_SECRET_KEY': 'a-real-50-char-secret-key-that-is-strong-enough!!'})
        assert mod.SECRET_KEY == 'a-real-50-char-secret-key-that-is-strong-enough!!'


class TestWebAuthnProdDefault:
    _KEY = 'a-real-50-char-secret-key-that-is-strong-enough!!'

    def test_insecure_origin_is_false_by_default(self):
        mod = _reload_prod({'DJANGO_SECRET_KEY': self._KEY})
        assert mod.MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN is False

    def test_insecure_origin_can_be_opted_in(self):
        mod = _reload_prod({
            'DJANGO_SECRET_KEY': self._KEY,
            'MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN': 'true',
        })
        assert mod.MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN is True

    def test_base_settings_default_is_also_false(self):
        import importlib, sys
        from unittest.mock import patch
        env = {
            'MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN': '',
            'OIDC_PROVIDER_URL': '', 'OIDC_CLIENT_ID': '',
            'OIDC_CLIENT_SECRET': '', 'OIDC_CLIENT_SECRET_FILE': '',
            'GOOGLE_CLIENT_ID': '', 'GOOGLE_CLIENT_SECRET': '',
            'GOOGLE_CLIENT_SECRET_FILE': '',
        }
        for key in list(sys.modules):
            if key.startswith('scd_reporting.settings'):
                del sys.modules[key]
        with patch.dict(__import__('os').environ, env):
            mod = importlib.import_module('scd_reporting.settings.base')
        assert mod.MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN is False
