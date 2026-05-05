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
