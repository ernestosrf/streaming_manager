import os
import sqlite3

import pytest

from flask_migrate import upgrade

from src.main import create_app
from src.models.db import db
from src.models.user import User
from src.models.content import Content


OLD_SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE content (
    id INTEGER PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    year INTEGER,
    type VARCHAR(20) NOT NULL,
    genre VARCHAR(100),
    poster_url VARCHAR(500),
    is_active BOOLEAN,
    created_at DATETIME
);
CREATE TABLE streaming_platform (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    logo_url VARCHAR(500),
    color VARCHAR(7),
    active BOOLEAN
);
CREATE TABLE content_streaming (
    content_id INTEGER NOT NULL,
    streaming_id INTEGER NOT NULL,
    available BOOLEAN,
    last_checked DATETIME,
    PRIMARY KEY (content_id, streaming_id),
    FOREIGN KEY (content_id) REFERENCES content(id),
    FOREIGN KEY (streaming_id) REFERENCES streaming_platform(id)
);
"""


def test_migration_assigns_existing_content_to_admin(tmp_path, monkeypatch):
    monkeypatch.setenv('ADMIN_USERNAME', 'admin')
    monkeypatch.setenv('ADMIN_PASSWORD', 'admin-password')
    monkeypatch.setenv('FLASK_SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')

    db_path = tmp_path / 'legacy.db'
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA foreign_keys=ON')
    conn.executescript(OLD_SCHEMA)
    conn.execute(
        "INSERT INTO streaming_platform (name, color, active) VALUES (?, ?, ?)",
        ('Netflix', '#E50914', 1),
    )
    conn.execute(
        "INSERT INTO content (title, year, type, genre, is_active) VALUES (?, ?, ?, ?, ?)",
        ('Watchlist Legado', 2020, 'movie', 'Drama', 1),
    )
    conn.execute(
        "INSERT INTO content_streaming (content_id, streaming_id, available) VALUES (?, ?, ?)",
        (1, 1, 1),
    )
    conn.commit()
    conn.close()

    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path.as_posix()}',
        'JWT_SECRET_KEY': 'test-jwt-secret',
        'SECRET_KEY': 'test-secret',
    })

    migrations_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'migrations'))
    with app.app_context():
        upgrade(directory=migrations_dir)
        admin = User.query.filter_by(role='admin').first()
        assert admin is not None
        assert admin.username == 'admin'
        contents = Content.query.all()
        assert len(contents) == 1
        assert contents[0].title == 'Watchlist Legado'
        assert contents[0].owner_id == admin.id
        assert len(contents[0].streamings) == 1


def _migration_app(db_path):
    return create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path.as_posix()}',
        'JWT_SECRET_KEY': 'test-jwt-secret',
        'SECRET_KEY': 'test-secret',
    })


def _table_names(db_path):
    conn = sqlite3.connect(db_path)
    try:
        return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()


def _content_columns(db_path):
    conn = sqlite3.connect(db_path)
    try:
        return {row[1] for row in conn.execute('PRAGMA table_info(content)')}
    finally:
        conn.close()


def test_downgrade_after_fresh_upgrade(tmp_path, monkeypatch):
    from flask_migrate import downgrade
    monkeypatch.setenv('ADMIN_USERNAME', 'admin')
    monkeypatch.setenv('ADMIN_PASSWORD', 'admin-password')
    db_path = tmp_path / 'fresh.db'
    migrations_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'migrations'))

    with _migration_app(db_path).app_context():
        upgrade(directory=migrations_dir)
        downgrade(directory=migrations_dir, revision='base')
        db.engine.dispose()

    assert 'users' not in _table_names(db_path)
    assert 'owner_id' not in _content_columns(db_path)


def test_downgrade_after_legacy_upgrade(tmp_path, monkeypatch):
    from flask_migrate import downgrade
    monkeypatch.setenv('ADMIN_USERNAME', 'admin')
    monkeypatch.setenv('ADMIN_PASSWORD', 'admin-password')
    db_path = tmp_path / 'legacy.db'
    conn = sqlite3.connect(db_path)
    conn.executescript(OLD_SCHEMA)
    conn.close()
    migrations_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'migrations'))

    with _migration_app(db_path).app_context():
        upgrade(directory=migrations_dir)
        downgrade(directory=migrations_dir, revision='base')
        db.engine.dispose()

    assert 'users' not in _table_names(db_path)
    assert 'owner_id' not in _content_columns(db_path)


def test_migration_rejects_invalid_admin_username(tmp_path, monkeypatch):
    monkeypatch.setenv('ADMIN_USERNAME', 'Admin User')
    monkeypatch.setenv('ADMIN_PASSWORD', 'admin-password')
    db_path = tmp_path / 'invalid.db'
    migrations_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'migrations'))

    with _migration_app(db_path).app_context():
        # O Flask-Migrate converte erros da migração em SystemExit.
        with pytest.raises(SystemExit):
            upgrade(directory=migrations_dir)
        db.engine.dispose()

    assert 'users' not in _table_names(db_path)
