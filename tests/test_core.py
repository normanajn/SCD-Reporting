"""Tests for core views: bug report submission (rate limiting, validation, auth)."""
import pytest

from django.core.cache import cache
from django.urls import reverse

from apps.accounts.models import User


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='tester', email='tester@example.com', password='pass')


class TestBugReportSubmit:
    def test_anonymous_redirected(self, client):
        resp = client.post(reverse('bug-report-submit'), {'title': 'x', 'body': 'y'})
        assert resp.status_code == 302
        assert '/login' in resp['Location'] or '/accounts' in resp['Location']

    def test_missing_title_rejected(self, client, user):
        client.force_login(user)
        resp = client.post(reverse('bug-report-submit'), {'title': '', 'body': 'some body'})
        assert resp.status_code == 302
        assert resp['Location'].endswith(reverse('bug-report'))

    def test_missing_body_rejected(self, client, user):
        client.force_login(user)
        resp = client.post(reverse('bug-report-submit'), {'title': 'A title', 'body': ''})
        assert resp.status_code == 302
        assert resp['Location'].endswith(reverse('bug-report'))

    def test_rate_limit_blocks_after_threshold(self, client, user, monkeypatch):
        submitted = []

        def fake_post(url, json, headers, timeout):
            submitted.append(json['title'])
            class R:
                status_code = 201
                def json(self): return {'number': len(submitted)}
            return R()

        monkeypatch.setattr('apps.core.views._resolve_github_token', lambda: 'fake-token')
        import requests as http_requests
        monkeypatch.setattr(http_requests, 'post', fake_post)

        client.force_login(user)
        for i in range(3):
            resp = client.post(reverse('bug-report-submit'), {'title': f'Bug {i}', 'body': 'desc'})
            assert resp.status_code == 302
            assert resp['Location'].endswith(reverse('about'))

        # Fourth submission should be rate-limited
        resp = client.post(reverse('bug-report-submit'), {'title': 'Bug 4', 'body': 'desc'})
        assert resp.status_code == 302
        assert resp['Location'].endswith(reverse('bug-report'))
        assert len(submitted) == 3  # GitHub API not called a 4th time

    def test_github_failure_shows_generic_message(self, client, user, monkeypatch):
        def fake_post(url, json, headers, timeout):
            class R:
                status_code = 500
                text = 'Internal Server Error'
                def json(self): return {'message': 'Server Error'}
            return R()

        monkeypatch.setattr('apps.core.views._resolve_github_token', lambda: 'fake-token')
        import requests as http_requests
        monkeypatch.setattr(http_requests, 'post', fake_post)

        client.force_login(user)
        resp = client.post(reverse('bug-report-submit'), {'title': 'Bug', 'body': 'desc'},
                           follow=True)
        content = resp.content.decode()
        assert 'Server Error' not in content
        assert 'could not be submitted' in content

    def test_no_token_shows_generic_message(self, client, user, monkeypatch):
        monkeypatch.setattr('apps.core.views._resolve_github_token', lambda: None)

        client.force_login(user)
        resp = client.post(reverse('bug-report-submit'), {'title': 'Bug', 'body': 'desc'},
                           follow=True)
        assert 'not configured' in resp.content.decode()
