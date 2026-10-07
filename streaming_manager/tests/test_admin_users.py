from src.models.content import Content
from src.models.db import db
from src.models.user import User, STATUS_ACTIVE, STATUS_INACTIVE, STATUS_PENDING, STATUS_REJECTED
from tests.conftest import add_content, auth_header, create_admin, create_user


def test_admin_lists_and_filters_users(client, app):
    create_admin()
    create_user('maria', 'senha1234', status=STATUS_PENDING)
    create_user('joao', 'senha1234', status=STATUS_ACTIVE)
    headers = auth_header(client, 'admin', 'admin-password')

    all_users = client.get('/api/admin/users', headers=headers)
    assert all_users.status_code == 200
    usernames = {user['username'] for user in all_users.get_json()}
    assert {'admin', 'maria', 'joao'} <= usernames

    pending = client.get('/api/admin/users?status=pending', headers=headers)
    assert [user['username'] for user in pending.get_json()] == ['maria']

    search = client.get('/api/admin/users?search=joa', headers=headers)
    assert [user['username'] for user in search.get_json()] == ['joao']


def test_approve_then_login(client, app):
    create_admin()
    maria = create_user('maria', 'senha1234', status=STATUS_PENDING)
    headers = auth_header(client, 'admin', 'admin-password')

    approve = client.post(f'/api/admin/users/{maria.id}/approve', headers=headers)
    assert approve.status_code == 200
    assert approve.get_json()['user']['status'] == STATUS_ACTIVE

    login = client.post('/api/auth/login', json={'username': 'maria', 'password': 'senha1234'})
    assert login.status_code == 200


def test_reject_activate_deactivate_and_reset_password(client, app):
    create_admin()
    maria = create_user('maria', 'senha1234', status=STATUS_PENDING)
    headers = auth_header(client, 'admin', 'admin-password')

    reject = client.post(f'/api/admin/users/{maria.id}/reject', headers=headers)
    assert reject.status_code == 200
    assert reject.get_json()['user']['status'] == STATUS_REJECTED

    activate = client.post(f'/api/admin/users/{maria.id}/activate', headers=headers)
    assert activate.status_code == 200
    assert activate.get_json()['user']['status'] == STATUS_ACTIVE

    deactivate = client.post(f'/api/admin/users/{maria.id}/deactivate', headers=headers)
    assert deactivate.status_code == 200
    assert deactivate.get_json()['user']['status'] == STATUS_INACTIVE
    assert client.get('/api/watchlists/maria').status_code == 404

    reset = client.post(f'/api/admin/users/{maria.id}/reset-password', json={
        'new_password': 'nova-senha-admin',
    }, headers=headers)
    assert reset.status_code == 200

    client.post(f'/api/admin/users/{maria.id}/activate', headers=headers)
    login = client.post('/api/auth/login', json={
        'username': 'maria',
        'password': 'nova-senha-admin',
    })
    assert login.status_code == 200


def test_admin_can_reset_own_password(client, app):
    admin = create_admin()
    headers = auth_header(client, 'admin', 'admin-password')
    response = client.post(f'/api/admin/users/{admin.id}/reset-password', json={
        'new_password': 'admin-nova-senha',
    }, headers=headers)
    assert response.status_code == 200
    login = client.post('/api/auth/login', json={
        'username': 'admin',
        'password': 'admin-nova-senha',
    })
    assert login.status_code == 200


def test_non_admin_cannot_access_admin_api(client, app):
    create_admin()
    create_user('maria', 'senha1234')
    headers = auth_header(client, 'maria', 'senha1234')
    response = client.get('/api/admin/users', headers=headers)
    assert response.status_code == 403


def test_delete_user_removes_contents(client, app):
    create_admin()
    maria = create_user('maria', 'senha1234')
    content = add_content(maria, title='Para Excluir')
    headers = auth_header(client, 'admin', 'admin-password')

    deleted = client.delete(f'/api/admin/users/{maria.id}', headers=headers)
    assert deleted.status_code == 200
    assert db.session.get(User, maria.id) is None
    assert db.session.get(Content, content.id) is None


def test_admin_user_list_is_paginated(client, app):
    create_admin()
    for index in range(5):
        create_user(f'user-{index}', 'senha1234')
    headers = auth_header(client, 'admin', 'admin-password')

    first = client.get('/api/admin/users?per_page=2&page=1', headers=headers)
    second = client.get('/api/admin/users?per_page=2&page=2', headers=headers)
    last = client.get('/api/admin/users?per_page=2&page=3', headers=headers)

    assert first.headers['X-Total-Count'] == '6'
    pages = [first.get_json(), second.get_json(), last.get_json()]
    assert [len(page) for page in pages] == [2, 2, 2]
    seen = [user['username'] for page in pages for user in page]
    assert len(set(seen)) == 6
    assert client.get('/api/admin/users?page=0', headers=headers).status_code == 400
