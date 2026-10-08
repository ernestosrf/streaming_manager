"""Suporte a múltiplos usuários: tabela users, owner_id e seed do admin.

Revision ID: 001_multiuser
Revises:
Create Date: 2026-04-09
"""
import os
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from werkzeug.security import generate_password_hash

from src.utils.validators import validate_admin_credentials

revision = '001_multiuser'
down_revision = None
branch_labels = None
depends_on = None


def _table_names(conn):
    return set(inspect(conn).get_table_names())


def _column_names(conn, table):
    return {column['name'] for column in inspect(conn).get_columns(table)}


def _create_users_table():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(length=30), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_status', 'users', ['status'], unique=False)


def _create_streaming_platform_table():
    op.create_table(
        'streaming_platform',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.UniqueConstraint('name'),
    )


def _create_content_table(with_owner=True, owner_nullable=False):
    columns = [
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('genre', sa.String(length=100), nullable=True),
        sa.Column('poster_url', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    ]
    if with_owner:
        columns.append(sa.Column('owner_id', sa.Integer(), nullable=owner_nullable))
        columns.append(sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name='fk_content_owner_id'))
    op.create_table('content', *columns)
    if with_owner:
        op.create_index('ix_content_owner_id', 'content', ['owner_id'], unique=False)


def _create_content_streaming_table():
    op.create_table(
        'content_streaming',
        sa.Column('content_id', sa.Integer(), nullable=False),
        sa.Column('streaming_id', sa.Integer(), nullable=False),
        sa.Column('available', sa.Boolean(), nullable=True),
        sa.Column('last_checked', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['content_id'], ['content.id']),
        sa.ForeignKeyConstraint(['streaming_id'], ['streaming_platform.id']),
        sa.PrimaryKeyConstraint('content_id', 'streaming_id'),
    )


def _require_admin_credentials():
    username = (os.environ.get('ADMIN_USERNAME') or '').strip()
    password = os.environ.get('ADMIN_PASSWORD') or ''
    error = validate_admin_credentials(username, password)
    if error:
        raise RuntimeError(f'{error} (obrigatório na primeira migração)')
    return username, password


def _seed_admin(conn):
    existing = conn.execute(sa.text("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1")).fetchone()
    if existing:
        return existing[0]

    username, password = _require_admin_credentials()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    conn.execute(
        sa.text(
            """
            INSERT INTO users (username, password_hash, role, status, created_at, approved_at)
            VALUES (:username, :password_hash, 'admin', 'active', :created_at, :approved_at)
            """
        ),
        {
            'username': username,
            'password_hash': generate_password_hash(password),
            'created_at': now,
            'approved_at': now,
        },
    )
    row = conn.execute(sa.text("SELECT id FROM users WHERE username = :username"), {'username': username}).fetchone()
    return row[0]


def upgrade():
    conn = op.get_bind()
    tables = _table_names(conn)
    has_admin = False
    if 'users' in tables:
        has_admin = conn.execute(
            sa.text("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1")
        ).fetchone() is not None
    if not has_admin:
        _require_admin_credentials()

    if 'users' not in tables:
        _create_users_table()

    admin_id = _seed_admin(conn)

    tables = _table_names(conn)
    if 'streaming_platform' not in tables:
        _create_streaming_platform_table()

    if 'content' not in tables:
        _create_content_table(with_owner=True, owner_nullable=False)
    else:
        columns = _column_names(conn, 'content')
        if 'owner_id' not in columns:
            # ADD COLUMN nativo evita recriar/dropar a tabela no SQLite.
            op.execute(sa.text('ALTER TABLE content ADD COLUMN owner_id INTEGER'))
            existing_indexes = {index['name'] for index in inspect(conn).get_indexes('content')}
            if 'ix_content_owner_id' not in existing_indexes:
                op.create_index('ix_content_owner_id', 'content', ['owner_id'], unique=False)

        conn.execute(
            sa.text('UPDATE content SET owner_id = :admin_id WHERE owner_id IS NULL'),
            {'admin_id': admin_id},
        )

        fk_names = {fk['name'] for fk in inspect(conn).get_foreign_keys('content')}
        owner_nullable = True
        for column in inspect(conn).get_columns('content'):
            if column['name'] == 'owner_id':
                owner_nullable = column['nullable']
                break

        if owner_nullable or 'fk_content_owner_id' not in fk_names:
            with op.batch_alter_table('content') as batch_op:
                batch_op.alter_column('owner_id', existing_type=sa.Integer(), nullable=False)
                if 'fk_content_owner_id' not in fk_names:
                    batch_op.create_foreign_key('fk_content_owner_id', 'users', ['owner_id'], ['id'])

    tables = _table_names(conn)
    if 'content_streaming' not in tables:
        _create_content_streaming_table()


def downgrade():
    conn = op.get_bind()
    tables = _table_names(conn)
    if 'content' in tables and 'owner_id' in _column_names(conn, 'content'):
        # O índice precisa sair antes da coluna, senão o batch do SQLite tenta recriá-lo.
        existing_indexes = {index['name'] for index in inspect(conn).get_indexes('content')}
        if 'ix_content_owner_id' in existing_indexes:
            op.drop_index('ix_content_owner_id', table_name='content')
        # O nome da FK varia: nomeada pela migração, gerada pelo Postgres ou sem nome no SQLite.
        owner_fk_names = [
            fk['name']
            for fk in inspect(conn).get_foreign_keys('content')
            if fk['constrained_columns'] == ['owner_id'] and fk['name']
        ]
        with op.batch_alter_table('content') as batch_op:
            for fk_name in owner_fk_names:
                batch_op.drop_constraint(fk_name, type_='foreignkey')
            batch_op.drop_column('owner_id')
    if 'users' in tables:
        op.drop_index('ix_users_status', table_name='users')
        op.drop_index('ix_users_username', table_name='users')
        op.drop_table('users')
