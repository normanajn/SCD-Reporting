import pytest
from django.contrib.auth import get_user_model

from apps.taxonomy.models import WorkGroup

User = get_user_model()


@pytest.fixture
def group(db):
    return WorkGroup.objects.create(name='Test Group', slug='test-group', is_active=True)


@pytest.fixture
def user_no_group(db):
    return User.objects.create_user(username='nogroupuser@x.com', email='nogroupuser@x.com', password='pass')


@pytest.fixture
def user_with_group(db, group):
    u = User.objects.create_user(username='groupuser@x.com', email='groupuser@x.com', password='pass')
    u.group = group
    u.save()
    return u


@pytest.mark.django_db
def test_select_group_page_shown_when_no_group(client, user_no_group, group):
    client.force_login(user_no_group)
    # Any normal page should redirect to select-group when groups exist
    resp = client.get('/entries/', follow=False)
    assert resp.status_code == 302
    assert resp['Location'] == '/select-group/'


@pytest.mark.django_db
def test_select_group_page_not_shown_when_no_groups_exist(client, user_no_group):
    # No WorkGroup objects — middleware should not redirect to select-group
    client.force_login(user_no_group)
    resp = client.get('/', follow=False)
    # Should reach the dashboard normally (200), not be sent to select-group
    assert resp.status_code == 200


@pytest.mark.django_db
def test_select_group_page_not_shown_when_group_already_set(client, user_with_group, group):
    client.force_login(user_with_group)
    resp = client.get('/entries/', follow=False)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_select_group_post_sets_group(client, user_no_group, group):
    client.force_login(user_no_group)
    resp = client.post('/select-group/', {'group': str(group.pk)})
    assert resp.status_code == 302
    user_no_group.refresh_from_db()
    assert user_no_group.group_id == group.pk


@pytest.mark.django_db
def test_select_group_skip_sets_session_flag(client, user_no_group, group):
    client.force_login(user_no_group)
    resp = client.post('/select-group/', {'group': ''})
    assert resp.status_code == 302
    assert client.session.get('_group_selection_done') is True
    # Subsequent requests should not redirect again this session
    resp2 = client.get('/entries/', follow=False)
    assert resp2.status_code == 200


@pytest.mark.django_db
def test_middleware_passthrough_for_allauth_paths(client, user_no_group, group):
    # /accounts/ paths must never be intercepted (logout, SSO callbacks, etc.)
    client.force_login(user_no_group)
    resp = client.get('/accounts/login/', follow=False)
    assert '/select-group/' not in resp.get('Location', '')
