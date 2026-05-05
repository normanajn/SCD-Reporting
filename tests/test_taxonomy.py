import pytest
from django.contrib.auth import get_user_model

from apps.taxonomy.models import Category, Project, Tag

User = get_user_model()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username='tax-admin', email='tax-admin@example.com',
        password='pass', role=User.Role.ADMIN,
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username='tax-user', email='tax-user@example.com',
        password='pass', role=User.Role.USER,
    )


# ── Model tests ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_project_slug_auto_generated():
    p = Project.objects.create(name='My Project')
    assert p.slug == 'my-project'


@pytest.mark.django_db
def test_project_slug_not_overwritten():
    p = Project.objects.create(name='DUNE', slug='dune-custom')
    assert p.slug == 'dune-custom'


@pytest.mark.django_db
def test_tag_name_lowercased_on_save():
    t = Tag.objects.create(name='  MachineLearning  ')
    assert t.name == 'machinelearning'


@pytest.mark.django_db
def test_tag_unique_constraint():
    Tag.objects.create(name='htmx')
    with pytest.raises(Exception):
        Tag.objects.create(name='htmx')


# ── Access control ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_projects_page_requires_admin(client, regular_user):
    client.force_login(regular_user)
    assert client.get('/taxonomy/projects/').status_code == 403


@pytest.mark.django_db
def test_projects_page_accessible_to_admin(client, admin_user):
    client.force_login(admin_user)
    assert client.get('/taxonomy/projects/').status_code == 200


@pytest.mark.django_db
def test_categories_page_requires_admin(client, regular_user):
    client.force_login(regular_user)
    assert client.get('/taxonomy/categories/').status_code == 403


@pytest.mark.django_db
def test_tag_autocomplete_requires_login(client):
    assert client.get('/taxonomy/tags/autocomplete/?q=du').status_code == 302


@pytest.mark.django_db
def test_tag_autocomplete_accessible_to_regular_user(client, regular_user):
    client.force_login(regular_user)
    assert client.get('/taxonomy/tags/autocomplete/?q=du').status_code == 200


# ── CRUD ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_project_via_post(client, admin_user):
    client.force_login(admin_user)
    resp = client.post('/taxonomy/projects/', {'name': 'Test', 'short_code': 'TST',
                                               'is_active': True, 'sort_order': 99})
    assert resp.status_code == 302
    assert Project.objects.filter(name='Test').exists()


@pytest.mark.django_db
def test_edit_project(client, admin_user):
    p = Project.objects.create(name='OldName')
    client.force_login(admin_user)
    resp = client.post(f'/taxonomy/projects/{p.pk}/edit/',
                       {'name': 'NewName', 'short_code': '', 'is_active': True, 'sort_order': 0})
    assert resp.status_code == 302
    p.refresh_from_db()
    assert p.name == 'NewName'


# ── seed_taxonomy ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_seed_taxonomy_idempotent():
    from django.core.management import call_command
    call_command('seed_taxonomy', verbosity=0)
    call_command('seed_taxonomy', verbosity=0)
    assert Project.objects.filter(name='DUNE').count() == 1
    assert Category.objects.filter(name='Scientific').count() == 1


@pytest.mark.django_db
def test_seed_taxonomy_creates_expected_data():
    from django.core.management import call_command
    call_command('seed_taxonomy', verbosity=0)
    assert Project.objects.count() == 5
    assert Category.objects.count() == 4
    assert Project.objects.filter(name='MicroBooNE').exists()
    assert Category.objects.filter(name='Outreach').exists()


# ── Tag autocomplete content ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_tag_autocomplete_returns_matching_tags(client, regular_user):
    Tag.objects.create(name='django')
    Tag.objects.create(name='htmx')
    client.force_login(regular_user)
    resp = client.get('/taxonomy/tags/autocomplete/?q=dj')
    assert b'django' in resp.content
    assert b'htmx' not in resp.content


@pytest.mark.django_db
def test_tag_autocomplete_empty_query_returns_empty(client, regular_user):
    client.force_login(regular_user)
    resp = client.get('/taxonomy/tags/autocomplete/?q=')
    assert resp.status_code == 200
    assert resp.content == b''
