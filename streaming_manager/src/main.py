import os
import sqlite3
import sys
from datetime import timedelta

from sqlalchemy import event
from sqlalchemy.engine import Engine

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from werkzeug.middleware.proxy_fix import ProxyFix

from src.models.db import db
from src.models.user import User  # noqa: F401
from src.models.content import Content, StreamingPlatform, ContentStreaming  # noqa: F401
from src.routes.content import content_bp
from src.routes.streaming import streaming_bp
from src.routes.auth import auth_bp
from src.routes.admin_users import admin_users_bp
from src.utils.auth import get_admin_user
from src.utils.rate_limit import limiter

migrate = Migrate()
jwt = JWTManager()


@event.listens_for(Engine, 'connect')
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute('PRAGMA foreign_keys=ON')
    cursor.close()


def _cors_origins():
    raw = os.environ.get('CORS_ORIGINS', 'http://localhost:5173,http://localhost:5000')
    origins = [origin.strip() for origin in raw.split(',') if origin.strip()]
    return origins or ['http://localhost:5173']


def create_app(config_overrides=None):
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY')
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
    app.config['JWT_ALGORITHM'] = 'HS256'

    database_url = os.environ.get('DATABASE_URL')
    if config_overrides and 'SQLALCHEMY_DATABASE_URI' in config_overrides:
        pass
    elif database_url:
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        db_dir = os.path.join(os.path.dirname(__file__), 'database')
        os.makedirs(db_dir, exist_ok=True)
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(db_dir, "app.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['RATELIMIT_STORAGE_URI'] = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')
    app.config['RATELIMIT_HEADERS_ENABLED'] = True

    if config_overrides:
        app.config.update(config_overrides)

    missing = [key for key in ('SECRET_KEY', 'JWT_SECRET_KEY') if not app.config.get(key)]
    if missing:
        raise RuntimeError(
            'Defina FLASK_SECRET_KEY e JWT_SECRET_KEY no ambiente (.env) antes de iniciar a aplicação. '
            f'Ausentes: {", ".join(missing)}'
        )

    trusted_proxies = int(os.environ.get('TRUSTED_PROXY_COUNT', '0'))
    if trusted_proxies > 0:
        # Atrás de proxy (ex.: Render), o IP real do cliente vem em X-Forwarded-For.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=trusted_proxies, x_proto=trusted_proxies)

    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db, directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'migrations'), render_as_batch=True)
    CORS(app, origins=_cors_origins(), expose_headers=['X-Total-Count'])

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(content_bp, url_prefix='/api')
    app.register_blueprint(streaming_bp, url_prefix='/api')
    app.register_blueprint(admin_users_bp, url_prefix='/api/admin')

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Recurso não encontrado.'}), 404

    @app.errorhandler(429)
    def rate_limited(error):
        return jsonify({'error': 'Muitas tentativas. Aguarde um pouco e tente novamente.'}), 429

    @app.route('/api/health')
    def health_check():
        return jsonify({'status': 'healthy', 'message': 'API is running'})

    @app.route('/api/meta')
    def meta():
        admin = get_admin_user()
        return jsonify({
            'admin_username': admin.username if admin else None,
        })

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        if path == 'api' or path.startswith('api/'):
            # Rotas de API inexistentes não devem cair no fallback da SPA.
            return not_found(None)

        static_folder_path = app.static_folder
        if static_folder_path is None:
            return 'Static folder not configured', 404

        if path != '' and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)

        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        return 'index.html not found', 404

    return app


app = create_app()

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', '').lower() in ('1', 'true')
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    app.run(host=host, port=5000, debug=debug)
