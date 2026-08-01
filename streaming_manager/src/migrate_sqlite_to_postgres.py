"""
Migração one-shot: copia dados do app.db (SQLite) para o Postgres.

USO: rode no primeiro deploy com DATABASE_URL apontando para o Postgres.
Depois do deploy bem-sucedido, REMOVA a chamada em main.py e este arquivo.

Idempotente: se o Postgres já tiver dados, a migração é ignorada.
"""
import os
import sqlite3
from datetime import datetime

from sqlalchemy import text

from src.models.content import Content, ContentStreaming, StreamingPlatform
from src.models.db import db

SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'database', 'app.db')


def _parse_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(value, fmt)
        except (TypeError, ValueError):
            continue
    return None


def _as_bool(value, default=True):
    if value is None:
        return default
    return bool(value)


def run_migration_if_needed():
    """Copia streaming_platform, content e content_streaming do SQLite para o DB atual."""
    uri = db.engine.url
    if uri.get_backend_name() == 'sqlite':
        print('[migrate] Destino é SQLite; nada a fazer.')
        return

    if not os.path.exists(SQLITE_PATH):
        print(f'[migrate] app.db não encontrado em {SQLITE_PATH}; pulando.')
        return

    existing_platforms = StreamingPlatform.query.count()
    existing_content = Content.query.count()
    if existing_platforms > 0 or existing_content > 0:
        print(
            f'[migrate] Postgres já possui dados '
            f'(platforms={existing_platforms}, content={existing_content}); pulando.'
        )
        return

    print(f'[migrate] Lendo SQLite de {SQLITE_PATH}...')
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    platforms = cur.execute(
        'SELECT id, name, logo_url, color, active FROM streaming_platform ORDER BY id'
    ).fetchall()
    contents = cur.execute(
        'SELECT id, title, year, type, genre, poster_url, is_active, created_at '
        'FROM content ORDER BY id'
    ).fetchall()
    links = cur.execute(
        'SELECT content_id, streaming_id, available, last_checked '
        'FROM content_streaming'
    ).fetchall()
    conn.close()

    content_ids = {row['id'] for row in contents}
    platform_ids = {row['id'] for row in platforms}

    print(
        f'[migrate] Encontrados: {len(platforms)} plataformas, '
        f'{len(contents)} conteúdos, {len(links)} vínculos.'
    )

    for row in platforms:
        db.session.add(
            StreamingPlatform(
                id=row['id'],
                name=row['name'],
                logo_url=row['logo_url'],
                color=row['color'],
                active=_as_bool(row['active'], True),
            )
        )

    for row in contents:
        db.session.add(
            Content(
                id=row['id'],
                title=row['title'],
                year=row['year'],
                type=row['type'],
                genre=row['genre'],
                poster_url=row['poster_url'],
                is_active=_as_bool(row['is_active'], True),
                created_at=_parse_datetime(row['created_at']),
            )
        )

    skipped = 0
    for row in links:
        if row['content_id'] not in content_ids or row['streaming_id'] not in platform_ids:
            skipped += 1
            continue
        db.session.add(
            ContentStreaming(
                content_id=row['content_id'],
                streaming_id=row['streaming_id'],
                available=_as_bool(row['available'], True),
                last_checked=_parse_datetime(row['last_checked']),
            )
        )

    db.session.commit()

    # Ajusta sequences do Postgres após inserir IDs explícitos
    if uri.get_backend_name() in ('postgresql', 'postgres'):
        with db.engine.begin() as connection:
            connection.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence('streaming_platform', 'id'), "
                    "COALESCE((SELECT MAX(id) FROM streaming_platform), 1))"
                )
            )
            connection.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence('content', 'id'), "
                    "COALESCE((SELECT MAX(id) FROM content), 1))"
                )
            )

    print(
        f'[migrate] Concluído. '
        f'Inseridos {len(platforms)} plataformas, {len(contents)} conteúdos, '
        f'{len(links) - skipped} vínculos'
        + (f' ({skipped} órfãos ignorados).' if skipped else '.')
    )
