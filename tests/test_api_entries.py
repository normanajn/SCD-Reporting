"""Tests for the JSON entry-create API, focused on the project/category/lab_priority
multi-select backward-compatibility contract."""
import json
from datetime import date, timedelta

import pytest
from django.urls import reverse

from apps.accounts.models import APIToken, User
from apps.entries.models import WorkItem
from apps.taxonomy.models import Category, LabPriority, Project


@pytest.fixture
def api_user(db):
    return User.objects.create_user(username='apiuser', email='api@example.com', password='pass')


@pytest.fixture
def token(db, api_user):
    return APIToken.rotate(api_user)


@pytest.fixture
def project(db):
    return Project.objects.create(name='DUNE', slug='dune')


@pytest.fixture
def project2(db):
    return Project.objects.create(name='NOvA', slug='nova')


@pytest.fixture
def category(db):
    return Category.objects.create(name='Scientific', slug='scientific')


def _post(client, token, payload):
    today = date.today()
    base = {
        'title': 'API entry',
        'description': 'work done',
        'period_kind': 'week',
        'period_start': today.isoformat(),
        'period_end': (today + timedelta(days=6)).isoformat(),
    }
    base.update(payload)
    return client.post(
        reverse('api-entry-create'),
        data=json.dumps(base),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {token.key}',
    )


class TestEntryCreateAPI:
    def test_single_slug_still_works(self, client, token, project, category):
        # Legacy clients send single 'project'/'category' slugs.
        resp = _post(client, token, {'project': 'dune', 'category': 'scientific'})
        assert resp.status_code == 201, resp.content
        data = resp.json()
        entry = WorkItem.objects.get(pk=data['id'])
        assert list(entry.projects.values_list('slug', flat=True)) == ['dune']
        assert list(entry.categories.values_list('slug', flat=True)) == ['scientific']
        # Response carries both plural lists and legacy singular keys.
        assert data['projects'] == ['dune']
        assert data['project'] == 'dune'
        assert data['categories'] == ['scientific']
        assert data['category'] == 'scientific'

    def test_list_input_creates_multiple(self, client, token, project, project2, category):
        resp = _post(client, token, {'projects': ['dune', 'nova'], 'categories': ['scientific']})
        assert resp.status_code == 201, resp.content
        data = resp.json()
        entry = WorkItem.objects.get(pk=data['id'])
        assert set(entry.projects.values_list('slug', flat=True)) == {'dune', 'nova'}
        assert set(data['projects']) == {'dune', 'nova'}

    def test_missing_project_is_an_error(self, client, token, category):
        resp = _post(client, token, {'categories': ['scientific']})
        assert resp.status_code == 400
        assert 'projects' in resp.json()['errors']

    def test_lab_priorities_optional_list(self, client, token, project, category, db):
        lp = LabPriority.objects.create(name='AI', slug='ai')
        resp = _post(client, token, {
            'project': 'dune', 'category': 'scientific', 'lab_priorities': ['ai'],
        })
        assert resp.status_code == 201, resp.content
        entry = WorkItem.objects.get(pk=resp.json()['id'])
        assert list(entry.lab_priorities.values_list('slug', flat=True)) == ['ai']
