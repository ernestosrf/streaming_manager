import pytest
from sqlalchemy.pool import StaticPool

from src.main import create_app
from src.models.db import db
from tests.conftest import add_platform, auth_header, create_admin, create_user


def test_password_change_invalidates_old_tokens(client, app):
    create_user('maria', 'senha1234')
    old_headers = auth_header(client, 'maria', 'senha1234')

    changed = client.post('/api/auth/change-password', json={
        'current_password': 'senha1234',
        'new_password': 'novasenha1',
    }, headers=old_headers)
    assert changed.status_code == 200
    new_token = changed.get_json()['access_token']

    assert client.get('/api/auth/verify', headers=old_headers).status_code == 401
    assert client.get('/api/auth/me', headers=old_headers).status_code == 401
    new_headers = {'Authorization': f'Bearer {new_token}'}
    assert client.get('/api/auth/me', headers=new_headers).status_code == 200


def test_admin_reset_invalidates_target_tokens(client, app):
    create_admin()
    maria = create_user('maria', 'senha1234')
    maria_headers = auth_header(client, 'maria', 'senha1234')
    admin_headers = auth_header(client, 'admin', 'admin-password')

    reset = client.post(f'/api/admin/users/{maria.id}/reset-password', json={
        'new_password': 'outra-senha',
    }, headers=admin_headers)
    assert reset.status_code == 200
    assert 'access_token' not in reset.get_json()
    assert client.get('/api/auth/me', headers=maria_headers).status_code == 401


def test_admin_reset_of_own_password_returns_new_token(client, app):
    admin = create_admin()
    headers = auth_header(client, 'admin', 'admin-password')
    reset = client.post(f'/api/admin/users/{admin.id}/reset-password', json={
        'new_password': 'admin-nova-senha',
    }, headers=headers)
    new_headers = {'Authorization': f"Bearer {reset.get_json()['access_token']}"}
    assert client.get('/api/admin/users', headers=headers).status_code == 401
    assert client.get('/api/admin/users', headers=new_headers).status_code == 200


@pytest.mark.parametrize('payload, message_fragment', [
    ({'title': '', 'type': 'movie'}, 'Título'),
    ({'title': 'x' * 201, 'type': 'movie'}, 'Título'),
    ({'title': 'Ok', 'type': 'documentary'}, 'Tipo'),
    ({'title': 'Ok', 'type': 'movie', 'year': 'abc'}, 'Ano'),
    ({'title': 'Ok', 'type': 'movie', 'genre': 'g' * 101}, 'Gênero'),
    ({'title': 'Ok', 'type': 'movie', 'poster_url': 'javascript:alert(1)'}, 'poster'),
    ({'title': 'Ok', 'type': 'movie', 'streaming_ids': '12'}, 'streaming_ids'),
    ({'title': 'Ok', 'type': 'movie', 'streaming_ids': [999]}, 'Streaming'),
])
def test_create_content_rejects_invalid_payload(client, app, payload, message_fragment):
    create_user('maria', 'senha1234')
    headers = auth_header(client, 'maria', 'senha1234')
    response = client.post('/api/content', json=payload, headers=headers)
    assert response.status_code == 400
    assert message_fragment in response.get_json()['error']


def test_update_content_validates_partial_payload(client, app):
    create_user('maria', 'senha1234')
    platform = add_platform()
    headers = auth_header(client, 'maria', 'senha1234')
    created = client.post('/api/content', json={
        'title': '  Matrix  ',
        'type': 'movie',
        'streaming_ids': [platform.id, platform.id],
    }, headers=headers)
    assert created.status_code == 201
    body = created.get_json()
    assert body['title'] == 'Matrix'
    assert len(body['streamings']) == 1

    content_id = body['id']
    assert client.put(f'/api/content/{content_id}', json={'title': None}, headers=headers).status_code == 400
    assert client.put(f'/api/content/{content_id}', json={'type': 'foo'}, headers=headers).status_code == 400
    ok = client.put(f'/api/content/{content_id}', json={'year': 1999}, headers=headers)
    assert ok.status_code == 200
    assert ok.get_json()['title'] == 'Matrix'


def test_login_is_rate_limited():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite://',
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'connect_args': {'check_same_thread': False},
            'poolclass': StaticPool,
        },
        'RATELIMIT_ENABLED': True,
    })
    with app.app_context():
        db.create_all()
        client = app.test_client()
        statuses = [
            client.post('/api/auth/login', json={'username': 'ninguem', 'password': 'x'}).status_code
            for _ in range(11)
        ]
        db.session.remove()
        db.drop_all()
    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429
