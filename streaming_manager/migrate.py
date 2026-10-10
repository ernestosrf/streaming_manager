"""Backup do SQLite (se houver) e execução das migrações versionadas."""
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask_migrate import upgrade

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
load_dotenv(os.path.join(ROOT, '.env'))


def backup_sqlite():
    db_path = os.path.join(ROOT, 'src', 'database', 'app.db')
    if not os.path.isfile(db_path):
        print('Nenhum arquivo SQLite encontrado; backup ignorado.')
        return None

    backup_dir = os.path.join(ROOT, 'src', 'database', 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    destination = os.path.join(backup_dir, f'app.db.{stamp}.bak')
    shutil.copy2(db_path, destination)
    print(f'Backup criado em {destination}')
    return destination


def sqlite_needs_admin_seed():
    db_path = os.path.join(ROOT, 'src', 'database', 'app.db')
    if not os.path.isfile(db_path):
        return True
    conn = sqlite3.connect(db_path)
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'users' not in tables:
            return True
        row = conn.execute("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1").fetchone()
        return row is None
    finally:
        conn.close()


def ensure_admin_credentials():
    if os.environ.get('DATABASE_URL'):
        return
    if not sqlite_needs_admin_seed():
        return
    from src.utils.validators import validate_admin_credentials

    username = (os.environ.get('ADMIN_USERNAME') or '').strip()
    password = os.environ.get('ADMIN_PASSWORD') or ''
    error = validate_admin_credentials(username, password)
    if error:
        raise SystemExit(
            f'{error}. Corrija o .env antes de executar a primeira migração. '
            'O banco atual não foi alterado.'
        )


def run_migrations():
    from src.main import create_app

    app = create_app()
    migrations_dir = os.path.join(ROOT, 'migrations')
    with app.app_context():
        upgrade(directory=migrations_dir)
    print('Migrações aplicadas com sucesso.')


if __name__ == '__main__':
    if os.environ.get('DATABASE_URL'):
        print('DATABASE_URL definido. Faça backup do Postgres (pg_dump) antes de continuar.')
    else:
        ensure_admin_credentials()
        backup_sqlite()
    run_migrations()
