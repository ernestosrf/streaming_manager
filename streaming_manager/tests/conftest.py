import os
import sys

import pytest
from sqlalchemy.pool import StaticPool

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

os.environ.setdefault('FLASK_SECRET_KEY', 'test-secret')
os.environ.setdefault('JWT_SECRET_KEY', 'test-jwt-secret')
os.environ.setdefault('ADMIN_USERNAME', 'admin')
os.environ.setdefault('ADMIN_PASSWORD', 'admin-password')
os.environ.setdefault('CORS_ORIGINS', 'http://localhost:5173')

from src.main import create_app
from src.models.db import db
from src.models.user import User, ROLE_ADMIN, ROLE_USER, STATUS_ACTIVE, STATUS_PENDING
from src.models.content import Content, StreamingPlatform, ContentStreaming


@pytest.fixture
def app():
    application = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite://',
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'connect_args': {'check_same_thread': False},
            'poolclass': StaticPool,
        },
        'JWT_SECRET_KEY': 'test-jwt-secret',
        'SECRET_KEY': 'test-secret',
    })
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def create_user(username, password, role=ROLE_USER, status=STATUS_ACTIVE):
    user = User(username=username, role=role, status=status)
    if status == STATUS_ACTIVE:
        from datetime import datetime
        user.approved_at = datetime.utcnow()
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def create_admin():
    return create_user('admin', 'admin-password', role=ROLE_ADMIN, status=STATUS_ACTIVE)


def auth_header(client, username, password):
    response = client.post('/api/auth/login', json={
        'username': username,
        'password': password,
    })
    data = response.get_json()
    token = data['access_token']
    return {'Authorization': f'Bearer {token}'}


def add_content(owner, title='Matrix', year=1999, content_type='movie', genre='Ação', active=True, streamings=None):
    content = Content(
        title=title,
        year=year,
        type=content_type,
        genre=genre,
        poster_url='http://example.com/poster.jpg',
        is_active=active,
        owner_id=owner.id,
    )
    db.session.add(content)
    db.session.flush()
    for streaming in streamings or []:
        db.session.add(ContentStreaming(
            content_id=content.id,
            streaming_id=streaming.id,
            available=True,
        ))
    db.session.commit()
    return content


def add_platform(name='Netflix', color='#E50914'):
    platform = StreamingPlatform(name=name, color=color, active=True)
    db.session.add(platform)
    db.session.commit()
    return platform
