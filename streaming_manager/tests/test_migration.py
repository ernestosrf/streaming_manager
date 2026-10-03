import os
import sqlite3

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
