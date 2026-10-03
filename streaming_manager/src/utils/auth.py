from functools import wraps
from flask import jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from src.models.db import db
from src.models.user import User, ROLE_ADMIN


def get_user_from_jwt():
    identity = get_jwt_identity()
    if identity is None:
        return None
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None
    return db.session.get(User, user_id)


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
