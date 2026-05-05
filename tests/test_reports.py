"""Tests for the reports app: access control, preview, and all five exporters."""
import json
from datetime import date, timedelta

import pytest

from django.urls import reverse

from apps.accounts.models import User
from apps.entries.models import WorkItem
from apps.taxonomy.models import Category, Project


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username='admin', email='admin@example.com', password='pass',
        role=User.Role.ADMIN,
    )


@pytest.fixture
def auditor_user(db):
    return User.objects.create_user(
        username='auditor', email='auditor@example.com', password='pass',
        role=User.Role.AUDITOR,
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username='user', email='user@example.com', password='pass',
    )


@pytest.fixture
def project(db):
    return Project.objects.create(name='DUNE', slug='dune')


@pytest.fixture
def category(db):
    return Category.objects.create(name='Scientific', slug='scientific')


@pytest.fixture
def entry(db, regular_user, project, category):
    today = date.today()
    start = today - timedelta(days=today.weekday())
    return WorkItem.objects.create(
        author=regular_user,
        title='Test entry',
        project=project,
        category=category,
        period_kind='week',
        period_start=start,
        period_end=start + timedelta(days=6),
        description='Some work done.',
    )


# ── Access control ────────────────────────────────────────────────────────────

class TestReportAccess:
    def test_anonymous_redirected(self, client):
        assert client.get(reverse('reports:index')).status_code == 302

    def test_regular_user_forbidden(self, client, regular_user):
        client.force_login(regular_user)
        assert client.get(reverse('reports:index')).status_code == 403

    def test_auditor_can_access(self, client, auditor_user):
        client.force_login(auditor_user)
        assert client.get(reverse('reports:index')).status_code == 200

    def test_admin_can_access(self, client, admin_user):
        client.force_login(admin_user)
        assert client.get(reverse('reports:index')).status_code == 200


# ── Preview ───────────────────────────────────────────────────────────────────

class TestReportPreview:
    def test_empty_filters_returns_all(self, client, admin_user, entry):
        client.force_login(admin_user)
        resp = client.post(reverse('reports:preview'), {})
        assert resp.status_code == 200
        assert b'Test entry' in resp.content

    def test_project_filter(self, client, admin_user, entry, project, category, db):
        other = Project.objects.create(name='CMS', slug='cms')
        client.force_login(admin_user)
        resp = client.post(reverse('reports:preview'), {'project': other.pk})
        assert b'Test entry' not in resp.content

    def test_author_email_filter(self, client, admin_user, entry):
        client.force_login(admin_user)
        resp = client.post(reverse('reports:preview'), {'author_email': 'nomatch@x.com'})
        assert b'Test entry' not in resp.content

    def test_no_match_shows_empty_message(self, client, admin_user):
        client.force_login(admin_user)
        resp = client.post(reverse('reports:preview'), {'author_email': 'nobody@nowhere.com'})
        assert b'No entries matched' in resp.content


# ── Exporters ─────────────────────────────────────────────────────────────────

class TestExporters:
    def _download(self, client, fmt, extra_data=None):
        data = extra_data or {}
        return client.post(reverse('reports:download', kwargs={'fmt': fmt}), data)

    def test_txt_download(self, client, admin_user, entry):
        client.force_login(admin_user)
        resp = self._download(client, 'txt')
        assert resp.status_code == 200
        assert resp['Content-Type'].startswith('text/plain')
        assert b'Test entry' in resp.content

    def test_csv_download(self, client, admin_user, entry):
        client.force_login(admin_user)
        resp = self._download(client, 'csv')
        assert resp.status_code == 200
        assert resp['Content-Type'].startswith('text/csv')
        assert b'Test entry' in resp.content
        assert b'title' in resp.content  # header row

    def test_json_download(self, client, admin_user, entry):
        client.force_login(admin_user)
        resp = self._download(client, 'json')
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert isinstance(data, list)
        assert any(r['title'] == 'Test entry' for r in data)

    def test_xlsx_download(self, client, admin_user, entry):
        client.force_login(admin_user)
        resp = self._download(client, 'xlsx')
        assert resp.status_code == 200
        assert 'spreadsheetml' in resp['Content-Type']
        # XLSX magic bytes: PK header
        assert resp.content[:2] == b'PK'

    def test_unknown_format_returns_400(self, client, admin_user):
        client.force_login(admin_user)
        resp = self._download(client, 'docx')
        assert resp.status_code == 400

    def test_download_respects_filter(self, client, admin_user, entry):
        client.force_login(admin_user)
        resp = self._download(client, 'json', {'author_email': 'nobody@nowhere.com'})
        data = json.loads(resp.content)
        assert data == []
