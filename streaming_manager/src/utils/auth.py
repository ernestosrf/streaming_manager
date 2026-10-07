import hashlib
import hmac
from functools import wraps
from flask import current_app, jsonify
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, jwt_required
from src.models.db import db
from src.models.user import User, ROLE_ADMIN


def _password_fingerprint(user):
    """Muda sempre que a senha muda, invalidando tokens emitidos antes da troca."""
    key = current_app.config['JWT_SECRET_KEY'].encode()
    return hmac.new(key, user.password_hash.encode(), hashlib.sha256).hexdigest()[:32]


def get_user_from_jwt():
    identity = get_jwt_identity()
    if identity is None:
        return None
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None
    user = db.session.get(User, user_id)
    if not user:
        return None
    token_fingerprint = get_jwt().get('pwd')
    if not token_fingerprint or not hmac.compare_digest(token_fingerprint, _password_fingerprint(user)):
        return None
    return user


def get_active_user():
    user = get_user_from_jwt()
    if not user or not user.is_active_account():
        return None
    return user


def issue_access_token(user):
    return create_access_token(
        identity=str(user.id),
        additional_claims={
            'role': user.role,
            'username': user.username,
            'pwd': _password_fingerprint(user),
        },
    )


def current_user_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user = get_active_user()
        if not user:
            return jsonify({'error': 'Conta inválida ou inativa.'}), 401
        return fn(user, *args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user = get_active_user()
        if not user:
            return jsonify({'error': 'Conta inválida ou inativa.'}), 401
        if user.role != ROLE_ADMIN:
            return jsonify({'error': 'Acesso negado. Apenas administradores.'}), 403
        return fn(user, *args, **kwargs)
    return wrapper


def get_admin_user():
    return User.query.filter_by(role=ROLE_ADMIN).order_by(User.id.asc()).first()
