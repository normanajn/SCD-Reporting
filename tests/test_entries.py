"""Tests for the entries app: WorkItem CRUD, period prefill, markdown preview."""
import pytest
from datetime import date, timedelta

from django.urls import reverse

from apps.accounts.models import User
from apps.entries.models import WorkItem
from apps.taxonomy.models import Category, Project, Tag


@pytest.fixture
def user(db):
    return User.objects.create_user(username='tester', email='tester@example.com', password='pass')


@pytest.fixture
def project(db):
    return Project.objects.create(name='TestProject', slug='testproject')


@pytest.fixture
def category(db):
    return Category.objects.create(name='TestCat', slug='testcat')


@pytest.fixture
def entry(db, user, project, category):
    today = date.today()
    return WorkItem.objects.create(
        author=user,
        title='My entry',
        project=project,
        category=category,
        period_kind='week',
        period_start=today - timedelta(days=today.weekday()),
        period_end=today - timedelta(days=today.weekday()) + timedelta(days=6),
        description='Hello **world**',
    )


# ── List ──────────────────────────────────────────────────────────────────────

class TestEntryList:
    def test_redirects_anonymous(self, client):
        resp = client.get(reverse('entries:list'))
        assert resp.status_code == 302

    def test_shows_own_entries(self, client, user, entry):
        client.force_login(user)
        resp = client.get(reverse('entries:list'))
        assert resp.status_code == 200
        assert entry.title in resp.content.decode()

    def test_hides_other_users_entries(self, db, client, entry, project, category):
        other = User.objects.create_user(username='other', email='other@example.com', password='pass')
        client.force_login(other)
        resp = client.get(reverse('entries:list'))
        assert entry.title not in resp.content.decode()


# ── Create ────────────────────────────────────────────────────────────────────

class TestEntryCreate:
    def test_get_renders_form(self, client, user):
        client.force_login(user)
        resp = client.get(reverse('entries:create'))
        assert resp.status_code == 200
        assert b'period_start' in resp.content

    def test_post_creates_entry(self, client, user, project, category):
        client.force_login(user)
        today = date.today()
        resp = client.post(reverse('entries:create'), {
            'title': 'New entry',
            'project': project.pk,
            'category': category.pk,
            'period_kind': 'week',
            'period_start': (today - timedelta(days=today.weekday())).isoformat(),
            'period_end':   (today - timedelta(days=today.weekday()) + timedelta(days=6)).isoformat(),
            'description': 'Test description',
            'tags_input': '',
        })
        assert resp.status_code == 302
        assert WorkItem.objects.filter(title='New entry', author=user).exists()

    def test_sets_author_to_current_user(self, client, user, project, category):
        client.force_login(user)
        today = date.today()
        client.post(reverse('entries:create'), {
            'title': 'Authored',
            'project': project.pk,
            'category': category.pk,
            'period_kind': 'week',
            'period_start': (today - timedelta(days=today.weekday())).isoformat(),
            'period_end':   (today - timedelta(days=today.weekday()) + timedelta(days=6)).isoformat(),
            'description': 'desc',
            'tags_input': '',
        })
        assert WorkItem.objects.get(title='Authored').author == user

    def test_post_with_tags_increments_use_count(self, client, user, project, category):
        tag = Tag.objects.create(name='mytag')
        client.force_login(user)
        today = date.today()
        client.post(reverse('entries:create'), {
            'title': 'Tagged',
            'project': project.pk,
            'category': category.pk,
            'period_kind': 'week',
            'period_start': (today - timedelta(days=today.weekday())).isoformat(),
            'period_end':   (today - timedelta(days=today.weekday()) + timedelta(days=6)).isoformat(),
            'description': 'desc',
            'tags_input': 'mytag',
        })
        tag.refresh_from_db()
        assert tag.use_count == 1


# ── Detail ────────────────────────────────────────────────────────────────────

class TestEntryDetail:
    def test_renders_markdown(self, client, user, entry):
        client.force_login(user)
        resp = client.get(reverse('entries:detail', kwargs={'pk': entry.pk}))
        assert resp.status_code == 200
        assert b'<strong>world</strong>' in resp.content

    def test_sanitizes_unsafe_markdown_html(self, client, user, entry):
        entry.description = 'Safe **bold** <img src=x onerror=alert(1)> [bad](javascript:alert(1))'
        entry.save()
        client.force_login(user)

        resp = client.get(reverse('entries:detail', kwargs={'pk': entry.pk}))

        assert resp.status_code == 200
        assert b'<strong>bold</strong>' in resp.content
        assert b'<img' not in resp.content
        assert b'onerror' not in resp.content
        assert b'javascript:' not in resp.content

    def test_other_user_gets_404(self, db, client, entry):
        other = User.objects.create_user(username='other2', email='other2@example.com', password='pass')
        client.force_login(other)
        resp = client.get(reverse('entries:detail', kwargs={'pk': entry.pk}))
        assert resp.status_code == 404

    def test_group_leader_can_view_others_entry(self, db, client, entry):
        leader = User.objects.create_user(username='leader', email='leader@example.com', password='pass',
                                          role=User.Role.GROUP_LEADER)
        client.force_login(leader)
        resp = client.get(reverse('entries:detail', kwargs={'pk': entry.pk}))
        assert resp.status_code == 200

    def test_functional_lead_can_view_others_entry(self, db, client, entry):
        lead = User.objects.create_user(username='flead', email='flead@example.com', password='pass',
                                        role=User.Role.FUNCTIONAL_LEAD)
        client.force_login(lead)
        resp = client.get(reverse('entries:detail', kwargs={'pk': entry.pk}))
        assert resp.status_code == 200

    def test_shows_author_display_name(self, client, user, entry):
        user.display_name = 'Alice Tester'
        user.save(update_fields=['display_name'])
        client.force_login(user)
        resp = client.get(reverse('entries:detail', kwargs={'pk': entry.pk}))
        assert resp.status_code == 200
        assert b'Alice Tester' in resp.content

    def test_shows_author_email_when_no_display_name(self, client, user, entry):
        user.display_name = ''
        user.save(update_fields=['display_name'])
        client.force_login(user)
        resp = client.get(reverse('entries:detail', kwargs={'pk': entry.pk}))
        assert resp.status_code == 200
        assert b'tester@example.com' in resp.content


# ── Edit ──────────────────────────────────────────────────────────────────────

class TestEntryEdit:
    def test_can_edit_own_entry(self, client, user, entry):
        client.force_login(user)
        resp = client.post(reverse('entries:edit', kwargs={'pk': entry.pk}), {
            'title': 'Updated title',
            'project': entry.project.pk,
            'category': entry.category.pk,
            'period_kind': entry.period_kind,
            'period_start': entry.period_start.isoformat(),
            'period_end':   entry.period_end.isoformat(),
            'description': entry.description,
            'tags_input': '',
        })
        assert resp.status_code == 302
        entry.refresh_from_db()
        assert entry.title == 'Updated title'

    def test_edit_form_shows_existing_dates(self, client, user, entry):
        client.force_login(user)
        resp = client.get(reverse('entries:edit', kwargs={'pk': entry.pk}))
        assert resp.status_code == 200
        assert entry.period_start.isoformat().encode() in resp.content
        assert entry.period_end.isoformat().encode() in resp.content

    def test_cannot_edit_other_users_entry(self, db, client, entry):
        other = User.objects.create_user(username='other3', email='other3@example.com', password='pass')
        client.force_login(other)
        resp = client.post(reverse('entries:edit', kwargs={'pk': entry.pk}), {
            'title': 'Hijacked',
            'project': entry.project.pk,
            'category': entry.category.pk,
            'period_kind': entry.period_kind,
            'period_start': entry.period_start.isoformat(),
            'period_end':   entry.period_end.isoformat(),
            'description': '',
            'tags_input': '',
        })
        assert resp.status_code == 404
        entry.refresh_from_db()
        assert entry.title != 'Hijacked'


# ── Delete ────────────────────────────────────────────────────────────────────

class TestEntryDelete:
    def test_delete_decrements_tag_use_count(self, client, user, project, category):
        tag = Tag.objects.create(name='deletetag', use_count=1)
        today = date.today()
        item = WorkItem.objects.create(
            author=user, title='To delete', project=project, category=category,
            period_kind='week',
            period_start=today - timedelta(days=today.weekday()),
            period_end=today - timedelta(days=today.weekday()) + timedelta(days=6),
            description='',
        )
        item.tags.add(tag)
        client.force_login(user)
        client.post(reverse('entries:delete', kwargs={'pk': item.pk}))
        tag.refresh_from_db()
        assert tag.use_count == 0
        assert not WorkItem.objects.filter(pk=item.pk).exists()


# ── HTMX: period prefill ──────────────────────────────────────────────────────

class TestPeriodPrefill:
    @pytest.mark.parametrize('kind', ['week', 'fortnight', 'month', 'custom'])
    def test_returns_date_inputs(self, client, user, kind):
        client.force_login(user)
        resp = client.get(reverse('entries:period-prefill') + f'?kind={kind}')
        assert resp.status_code == 200
        assert b'period_start' in resp.content
        assert b'period_end' in resp.content

    def test_week_start_is_monday(self, client, user):
        client.force_login(user)
        resp = client.get(reverse('entries:period-prefill') + '?kind=week')
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        assert monday.isoformat().encode() in resp.content


# ── HTMX: markdown preview ────────────────────────────────────────────────────

class TestMarkdownPreview:
    def test_renders_html(self, client, user):
        client.force_login(user)
        resp = client.post(reverse('entries:markdown-preview'), {'description': '**bold**'})
        assert resp.status_code == 200
        assert b'<strong>bold</strong>' in resp.content

    def test_sanitizes_unsafe_html(self, client, user):
        client.force_login(user)
        resp = client.post(reverse('entries:markdown-preview'), {
            'description': '<script>alert(1)</script><img src=x onerror=alert(1)> **ok**',
        })
        assert resp.status_code == 200
        assert b'<strong>ok</strong>' in resp.content
        assert b'<script' not in resp.content
        assert b'<img' not in resp.content
        assert b'onerror' not in resp.content

    def test_empty_description_returns_empty(self, client, user):
        client.force_login(user)
        resp = client.post(reverse('entries:markdown-preview'), {'description': ''})
        assert resp.status_code == 200
