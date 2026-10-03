from src.models.user import STATUS_PENDING, STATUS_REJECTED, STATUS_INACTIVE
from tests.conftest import create_admin, create_user, auth_header


def test_register_creates_pending_user(client, app):
    response = client.post('/api/auth/register', json={
        'username': 'maria',
        'password': 'senha1234',
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['user']['status'] == STATUS_PENDING
    assert data['user']['role'] == 'user'


def test_register_rejects_reserved_and_invalid_usernames(client):
    reserved = client.post('/api/auth/register', json={
        'username': 'admin',
        'password': 'senha1234',
    })
    assert reserved.status_code == 400

    invalid = client.post('/api/auth/register', json={
        'username': 'Maria_1',
        'password': 'senha1234',
    })
    assert invalid.status_code == 400

    short_password = client.post('/api/auth/register', json={
        'username': 'joao',
        'password': '123',
    })
    assert short_password.status_code == 400


def test_pending_login_returns_specific_message(client, app):
    create_user('pendente', 'senha1234', status=STATUS_PENDING)
    response = client.post('/api/auth/login', json={
        'username': 'pendente',
        'password': 'senha1234',
    })
    assert response.status_code == 403
    assert 'aprovação' in response.get_json()['error'].lower()


def test_rejected_and_inactive_cannot_login(client, app):
    create_user('rejeitado', 'senha1234', status=STATUS_REJECTED)
    create_user('inativo', 'senha1234', status=STATUS_INACTIVE)

    rejected = client.post('/api/auth/login', json={
        'username': 'rejeitado',
        'password': 'senha1234',
    })
    assert rejected.status_code == 403
    assert 'rejeitada' in rejected.get_json()['error'].lower()

    inactive = client.post('/api/auth/login', json={
        'username': 'inativo',
        'password': 'senha1234',
    })
    assert inactive.status_code == 403
    assert 'desativada' in inactive.get_json()['error'].lower()


def test_invalid_credentials(client, app):
    create_user('maria', 'senha1234')
    response = client.post('/api/auth/login', json={
        'username': 'maria',
        'password': 'erradaaaa',
    })
    assert response.status_code == 401


def test_login_and_verify_return_id_and_role(client, app):
    create_admin()
    response = client.post('/api/auth/login', json={
        'username': 'admin',
        'password': 'admin-password',
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['user']['role'] == 'admin'
    assert 'access_token' in data

    verify = client.get('/api/auth/verify', headers={
        'Authorization': f"Bearer {data['access_token']}",
    })
    assert verify.status_code == 200
    assert verify.get_json()['user']['username'] == 'admin'


def test_change_password_requires_current_password(client, app):
    create_user('maria', 'senha1234')
    headers = auth_header(client, 'maria', 'senha1234')

    wrong = client.post('/api/auth/change-password', json={
        'current_password': 'outra',
        'new_password': 'novasenha1',
    }, headers=headers)
    assert wrong.status_code == 400

    ok = client.post('/api/auth/change-password', json={
        'current_password': 'senha1234',
        'new_password': 'novasenha1',
    }, headers=headers)
    assert ok.status_code == 200

    old_login = client.post('/api/auth/login', json={
        'username': 'maria',
        'password': 'senha1234',
    })
    assert old_login.status_code == 401

    new_login = client.post('/api/auth/login', json={
        'username': 'maria',
        'password': 'novasenha1',
    })
    assert new_login.status_code == 200
