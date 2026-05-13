import importlib
import os
import sys
from unittest.mock import patch

import pytest


# Keys to neutralise so a developer's real environment doesn't bleed into tests
_OIDC_ENV_KEYS = {
    'OIDC_PROVIDER_URL': '',
    'OIDC_CLIENT_ID': '',
    'OIDC_CLIENT_SECRET': '',
    'OIDC_CLIENT_SECRET_FILE': '',
    'GOOGLE_CLIENT_ID': '',
    'GOOGLE_CLIENT_SECRET': '',
    'GOOGLE_CLIENT_SECRET_FILE': '',
}


def _reload_base(overrides=None):
    """Re-import scd_reporting.settings.base with a controlled environment."""
    env = {**_OIDC_ENV_KEYS, **(overrides or {})}
    for key in list(sys.modules):
        if key.startswith('scd_reporting.settings'):
            del sys.modules[key]
    with patch.dict(os.environ, env):
        return importlib.import_module('scd_reporting.settings.base')


class TestOidcEnabled:
    def test_enabled_when_all_three_vars_set(self):
        mod = _reload_base({
            'OIDC_PROVIDER_URL': 'https://idp.example.com/realms/demo',
            'OIDC_CLIENT_ID': 'my-client',
            'OIDC_CLIENT_SECRET': 'my-secret',
        })
        assert mod.OIDC_ENABLED is True

    def test_disabled_when_secret_missing(self):
        mod = _reload_base({
            'OIDC_PROVIDER_URL': 'https://idp.example.com/realms/demo',
            'OIDC_CLIENT_ID': 'my-client',
        })
        assert mod.OIDC_ENABLED is False

    def test_disabled_when_url_missing(self):
        mod = _reload_base({
            'OIDC_CLIENT_ID': 'my-client',
            'OIDC_CLIENT_SECRET': 'my-secret',
        })
        assert mod.OIDC_ENABLED is False

    def test_disabled_when_client_id_missing(self):
        mod = _reload_base({
            'OIDC_PROVIDER_URL': 'https://idp.example.com/realms/demo',
            'OIDC_CLIENT_SECRET': 'my-secret',
        })
        assert mod.OIDC_ENABLED is False

    def test_well_known_suffix_stripped(self):
        mod = _reload_base({
            'OIDC_PROVIDER_URL': 'https://idp.example.com/realms/demo/.well-known/openid-configuration',
            'OIDC_CLIENT_ID': 'my-client',
            'OIDC_CLIENT_SECRET': 'my-secret',
        })
        assert mod.OIDC_ENABLED is True
        server_url = mod.SOCIALACCOUNT_PROVIDERS['openid_connect']['APPS'][0]['settings']['server_url']
        assert server_url == 'https://idp.example.com/realms/demo'

    def test_secret_passed_to_provider(self):
        mod = _reload_base({
            'OIDC_PROVIDER_URL': 'https://idp.example.com/realms/demo',
            'OIDC_CLIENT_ID': 'my-client',
            'OIDC_CLIENT_SECRET': 'my-secret',
        })
        secret = mod.SOCIALACCOUNT_PROVIDERS['openid_connect']['APPS'][0]['secret']
        assert secret == 'my-secret'


class TestOidcSecretFile:
    def test_secret_read_from_file(self, tmp_path):
        secret_file = tmp_path / 'oidc_secret'
        secret_file.write_text('file-secret\n')
        mod = _reload_base({
            'OIDC_PROVIDER_URL': 'https://idp.example.com/realms/demo',
            'OIDC_CLIENT_ID': 'my-client',
            'OIDC_CLIENT_SECRET_FILE': str(secret_file),
        })
        assert mod.OIDC_ENABLED is True
        secret = mod.SOCIALACCOUNT_PROVIDERS['openid_connect']['APPS'][0]['secret']
        assert secret == 'file-secret'

    def test_file_takes_precedence_over_env_var(self, tmp_path):
        secret_file = tmp_path / 'oidc_secret'
        secret_file.write_text('file-secret')
        mod = _reload_base({
            'OIDC_PROVIDER_URL': 'https://idp.example.com/realms/demo',
            'OIDC_CLIENT_ID': 'my-client',
            'OIDC_CLIENT_SECRET_FILE': str(secret_file),
            'OIDC_CLIENT_SECRET': 'env-secret',
        })
        secret = mod.SOCIALACCOUNT_PROVIDERS['openid_connect']['APPS'][0]['secret']
        assert secret == 'file-secret'

    def test_unreadable_secret_file_raises(self, tmp_path):
        bad_path = str(tmp_path / 'nonexistent.txt')
        with pytest.raises(Exception, match='OIDC_CLIENT_SECRET_FILE'):
            _reload_base({
                'OIDC_PROVIDER_URL': 'https://idp.example.com/realms/demo',
                'OIDC_CLIENT_ID': 'my-client',
                'OIDC_CLIENT_SECRET_FILE': bad_path,
            })
