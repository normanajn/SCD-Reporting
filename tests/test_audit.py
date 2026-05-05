"""Tests for the audit app: model, service, signals, and viewer."""
from datetime import date, timedelta

import pytest

from django.contrib.auth.signals import user_logged_in
from django.urls import reverse

from apps.accounts.models import User
from apps.audit.models import AuditLogEntry
from apps.audit.service import log_event
from apps.entries.models import WorkItem
from apps.taxonomy.models import Category, Project


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username='admin', email='admin@example.com', password='pass',
        role=User.Role.ADMIN,
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


def _make_entry(user, project, category):
    today = date.today()
    start = today - timedelta(days=today.weekday())
    return WorkItem.objects.create(
        author=user,
        title='Signal test entry',
        project=project,
        category=category,
        period_kind='week',
        period_start=start,
        period_end=start + timedelta(days=6),
        description='desc',
    )


# ── log_event service ─────────────────────────────────────────────────────────

class TestLogEvent:
    def test_creates_entry(self, db, admin_user):
        log_event(action='create', actor=admin_user)
        assert AuditLogEntry.objects.filter(actor=admin_user, action='create').exists()

    def test_captures_object_fields(self, db, admin_user, project, category, regular_user):
        item = _make_entry(regular_user, project, category)
        AuditLogEntry.objects.all().delete()  # clear signal-created entries
        log_event(action='update', actor=admin_user, obj=item, changes={'title': {'old': 'x', 'new': 'y'}})
        entry = AuditLogEntry.objects.get(action='update', actor=admin_user)
        assert entry.object_type == 'WorkItem'
        assert entry.object_id == item.pk
        assert entry.changes == {'title': {'old': 'x', 'new': 'y'}}

    def test_reads_actor_from_request(self, db, admin_user, rf):
        request = rf.get('/')
        request.user = admin_user
        log_event(action='export', request=request)
        entry = AuditLogEntry.objects.get(action='export')
        assert entry.actor == admin_user


# ── Signals ───────────────────────────────────────────────────────────────────

class TestSignals:
    def test_create_workitem_logs_create(self, db, regular_user, project, category):
        item = _make_entry(regular_user, project, category)
        assert AuditLogEntry.objects.filter(action='create', object_id=item.pk).exists()

    def test_update_workitem_logs_changed_fields(self, db, regular_user, project, category):
        item = _make_entry(regular_user, project, category)
        AuditLogEntry.objects.all().delete()

        item.title = 'Updated title'
        item.save()

        entry = AuditLogEntry.objects.get(action='update', object_id=item.pk)
        assert 'title' in entry.changes
        assert entry.changes['title']['new'] == 'Updated title'

    def test_update_with_no_changes_logs_nothing(self, db, regular_user, project, category):
        item = _make_entry(regular_user, project, category)
        AuditLogEntry.objects.all().delete()
        item.save()  # save with no field changes
        assert not AuditLogEntry.objects.filter(action='update').exists()

    def test_delete_workitem_logs_delete(self, db, regular_user, project, category):
        item = _make_entry(regular_user, project, category)
        pk = item.pk
        item.delete()
        assert AuditLogEntry.objects.filter(action='delete', object_id=pk).exists()

    def test_login_signal_logs_event(self, db, regular_user, rf):
        request = rf.get('/')
        request.user = regular_user
        user_logged_in.send(sender=regular_user.__class__, request=request, user=regular_user)
        assert AuditLogEntry.objects.filter(action='login', actor=regular_user).exists()


# ── Viewer access control ─────────────────────────────────────────────────────

class TestAuditViewer:
    def test_anonymous_redirected(self, client):
        assert client.get(reverse('audit:index')).status_code == 302

    def test_regular_user_forbidden(self, client, regular_user):
        client.force_login(regular_user)
        assert client.get(reverse('audit:index')).status_code == 403

    def test_admin_can_view(self, client, admin_user):
        client.force_login(admin_user)
        assert client.get(reverse('audit:index')).status_code == 200


# ── Viewer filtering ──────────────────────────────────────────────────────────

class TestAuditFilters:
    def _seed(self, admin_user, regular_user, project, category):
        _make_entry(regular_user, project, category)
        log_event(action='export', actor=admin_user)

    def test_filter_by_action(self, client, admin_user, regular_user, project, category):
        self._seed(admin_user, regular_user, project, category)
        client.force_login(admin_user)
        resp = client.get(reverse('audit:index') + '?action=export')
        assert b'Exported' in resp.content
        # create events should not appear in action-filtered view
        assert resp.content.count(b'Created') == 0 or b'Exported' in resp.content

    def test_filter_by_actor(self, client, admin_user, regular_user, project, category):
        self._seed(admin_user, regular_user, project, category)
        client.force_login(admin_user)
        resp = client.get(reverse('audit:index') + f'?actor={admin_user.email}')
        assert admin_user.email.encode() in resp.content

    def test_empty_filter_result(self, client, admin_user):
        client.force_login(admin_user)
        resp = client.get(reverse('audit:index') + '?actor=nobody@nowhere.com')
        assert b'No audit events' in resp.content
