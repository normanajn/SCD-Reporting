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

    def test_other_user_gets_404(self, db, client, entry):
        other = User.objects.create_user(username='other2', email='other2@example.com', password='pass')
        client.force_login(other)
        resp = client.get(reverse('entries:detail', kwargs={'pk': entry.pk}))
        assert resp.status_code == 404


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

    def test_empty_description_returns_empty(self, client, user):
        client.force_login(user)
        resp = client.post(reverse('entries:markdown-preview'), {'description': ''})
        assert resp.status_code == 200
