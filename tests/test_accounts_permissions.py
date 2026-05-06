import pytest
from django.test import RequestFactory
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def make_user(db):
    def _make(role=User.Role.USER, **kwargs):
        kwargs.setdefault('username', f'user_{role}')
        kwargs.setdefault('email', f'{kwargs["username"]}@example.com')
        kwargs.setdefault('password', 'pass')
        return User.objects.create_user(role=role, **kwargs)
    return _make


@pytest.mark.django_db
def test_role_choices_exist():
    assert User.Role.USER == 'user'
    assert User.Role.ADMIN == 'admin'
    assert User.Role.AUDITOR == 'auditor'


@pytest.mark.django_db
def test_is_scd_admin_property(make_user):
    admin = make_user(role=User.Role.ADMIN, username='admin1', email='admin1@example.com')
    user = make_user(role=User.Role.USER, username='user1', email='user1@example.com')
    auditor = make_user(role=User.Role.AUDITOR, username='aud1', email='aud1@example.com')

    assert admin.is_scd_admin is True
    assert user.is_scd_admin is False
    assert auditor.is_scd_admin is False


@pytest.mark.django_db
def test_is_auditor_property(make_user):
    admin = make_user(role=User.Role.ADMIN, username='admin2', email='admin2@example.com')
    user = make_user(role=User.Role.USER, username='user2', email='user2@example.com')
    auditor = make_user(role=User.Role.AUDITOR, username='aud2', email='aud2@example.com')

    assert admin.is_auditor is True    # admins are also auditors
    assert auditor.is_auditor is True
    assert user.is_auditor is False


@pytest.mark.django_db
def test_login_redirect_for_anonymous(client):
    response = client.get('/')
    assert response.status_code == 302
    assert '/accounts/login/' in response['Location']


@pytest.mark.django_db
def test_admin_users_requires_admin(client, make_user):
    regular = make_user(role=User.Role.USER, username='reg1', email='reg1@example.com')
    client.force_login(regular)
    response = client.get('/admin-users/')
    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_users_accessible_to_admin(client, make_user):
    admin = make_user(role=User.Role.ADMIN, username='adm1', email='adm1@example.com')
    client.force_login(admin)
    response = client.get('/admin-users/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_profile_accessible_to_all_auth_users(client, make_user):
    user = make_user(role=User.Role.USER, username='prof1', email='prof1@example.com')
    client.force_login(user)
    response = client.get('/profile/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_set_password_requires_admin(client, make_user):
    target = make_user(role=User.Role.USER, username='tgt1', email='tgt1@example.com')
    regular = make_user(role=User.Role.USER, username='reg2', email='reg2@example.com')
    client.force_login(regular)
    assert client.get(f'/admin-users/{target.pk}/set-password/').status_code == 403


@pytest.mark.django_db
def test_set_password_updates_password(client, make_user):
    admin = make_user(role=User.Role.ADMIN, username='adm2', email='adm2@example.com')
    target = make_user(role=User.Role.USER, username='tgt2', email='tgt2@example.com')
    client.force_login(admin)
    resp = client.post(f'/admin-users/{target.pk}/set-password/', {
        'new_password1': 'newpassword99',
        'new_password2': 'newpassword99',
    })
    assert resp.status_code == 302
    target.refresh_from_db()
    assert target.check_password('newpassword99')


@pytest.mark.django_db
def test_set_password_mismatch_shows_error(client, make_user):
    admin = make_user(role=User.Role.ADMIN, username='adm3', email='adm3@example.com')
    target = make_user(role=User.Role.USER, username='tgt3', email='tgt3@example.com')
    client.force_login(admin)
    resp = client.post(f'/admin-users/{target.pk}/set-password/', {
        'new_password1': 'abc',
        'new_password2': 'xyz',
    })
    assert resp.status_code == 200
    assert b'do not match' in resp.content


@pytest.mark.django_db
def test_delete_user_requires_admin(client, make_user):
    target = make_user(role=User.Role.USER, username='tgt4', email='tgt4@example.com')
    regular = make_user(role=User.Role.USER, username='reg3', email='reg3@example.com')
    client.force_login(regular)
    assert client.post(f'/admin-users/{target.pk}/delete/').status_code == 403


@pytest.mark.django_db
def test_delete_user_removes_account(client, make_user):
    admin = make_user(role=User.Role.ADMIN, username='adm4', email='adm4@example.com')
    target = make_user(role=User.Role.USER, username='tgt5', email='tgt5@example.com')
    client.force_login(admin)
    resp = client.post(f'/admin-users/{target.pk}/delete/')
    assert resp.status_code == 302
    assert not User.objects.filter(pk=target.pk).exists()


@pytest.mark.django_db
def test_delete_self_is_blocked(client, make_user):
    admin = make_user(role=User.Role.ADMIN, username='adm5', email='adm5@example.com')
    client.force_login(admin)
    resp = client.post(f'/admin-users/{admin.pk}/delete/')
    assert resp.status_code == 302
    assert User.objects.filter(pk=admin.pk).exists()


@pytest.mark.django_db
def test_delete_user_with_entries_is_blocked(client, make_user, db):
    from datetime import date, timedelta
    from apps.entries.models import WorkItem
    from apps.taxonomy.models import Project, Category

    admin = make_user(role=User.Role.ADMIN, username='adm6', email='adm6@example.com')
    target = make_user(role=User.Role.USER, username='tgt6', email='tgt6@example.com')
    project  = Project.objects.create(name='P1', slug='p1')
    category = Category.objects.create(name='C1', slug='c1')
    today = date.today()
    WorkItem.objects.create(
        author=target, title='entry', project=project, category=category,
        period_kind='week',
        period_start=today - timedelta(days=today.weekday()),
        period_end=today - timedelta(days=today.weekday()) + timedelta(days=6),
        description='desc',
    )
    client.force_login(admin)
    resp = client.post(f'/admin-users/{target.pk}/delete/')
    assert resp.status_code == 302
    assert User.objects.filter(pk=target.pk).exists()  # not deleted


@pytest.mark.django_db
def test_seed_admin_creates_user(db):
    from django.core.management import call_command
    import os

    os.environ['SCD_INITIAL_ADMIN_USERNAME'] = 'test-seed-admin'
    os.environ['SCD_INITIAL_ADMIN_EMAIL'] = 'seed@example.com'
    os.environ['SCD_INITIAL_ADMIN_PASSWORD'] = 'testpass123'
    try:
        call_command('seed_admin', verbosity=0)
        assert User.objects.filter(username='test-seed-admin').exists()
        # idempotent
        call_command('seed_admin', verbosity=0)
        assert User.objects.filter(username='test-seed-admin').count() == 1
    finally:
        del os.environ['SCD_INITIAL_ADMIN_USERNAME']
        del os.environ['SCD_INITIAL_ADMIN_EMAIL']
        del os.environ['SCD_INITIAL_ADMIN_PASSWORD']
