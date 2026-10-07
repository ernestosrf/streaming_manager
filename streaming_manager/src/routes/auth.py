from functools import lru_cache

from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from src.models.db import db
from src.models.user import User, ROLE_USER, STATUS_PENDING, STATUS_ACTIVE, STATUS_INACTIVE, STATUS_REJECTED
from src.utils.auth import current_user_required, get_user_from_jwt, issue_access_token
from src.utils.rate_limit import limiter
from src.utils.validators import validate_password, validate_username
from flask_jwt_extended import jwt_required

auth_bp = Blueprint('auth', __name__)

STATUS_LOGIN_MESSAGES = {
    STATUS_PENDING: 'Sua conta está aguardando aprovação do administrador.',
    STATUS_REJECTED: 'Sua conta foi rejeitada.',
    STATUS_INACTIVE: 'Sua conta está desativada.',
}


@lru_cache(maxsize=1)
def _dummy_password_hash():
    return generate_password_hash('dummy-password-for-timing')


@auth_bp.route('/register', methods=['POST'])
@limiter.limit('5 per hour')
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password')

    username_error = validate_username(username)
    if username_error:
        return jsonify({'error': username_error}), 400

    password_error = validate_password(password)
    if password_error:
        return jsonify({'error': password_error}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Este username já está em uso.'}), 409

    user = User(
        username=username,
        role=ROLE_USER,
        status=STATUS_PENDING,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({
        'message': 'Cadastro realizado. Aguarde a aprovação do administrador para entrar.',
        'user': user.to_dict(),
    }), 201


@auth_bp.route('/login', methods=['POST'])
@limiter.limit('10 per minute; 50 per hour')
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username e senha são obrigatórios.'}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        # Mesmo custo de hash que um usuário existente, para não revelar quais usernames existem.
        check_password_hash(_dummy_password_hash(), password)
        return jsonify({'error': 'Credenciais inválidas.'}), 401
    if not user.check_password(password):
        return jsonify({'error': 'Credenciais inválidas.'}), 401

    if user.status != STATUS_ACTIVE:
        message = STATUS_LOGIN_MESSAGES.get(user.status, 'Esta conta não pode entrar.')
        return jsonify({
            'error': message,
            'status': user.status,
        }), 403

    access_token = issue_access_token(user)
    return jsonify({
        'access_token': access_token,
        'message': 'Login realizado com sucesso',
        'expires_in': '24 horas',
        'user': user.to_dict(),
    }), 200


@auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    user = get_user_from_jwt()
    if not user:
        return jsonify({'error': 'Token inválido.'}), 401
    if not user.is_active_account():
        message = STATUS_LOGIN_MESSAGES.get(user.status, 'Esta conta não pode entrar.')
        return jsonify({'error': message, 'status': user.status, 'valid': False}), 401

    return jsonify({
        'valid': True,
        'user': user.to_dict(),
        'message': 'Token válido',
    }), 200


@auth_bp.route('/me', methods=['GET'])
@current_user_required
def me(current_user):
    return jsonify({'user': current_user.to_dict(include_private=True)}), 200


@auth_bp.route('/logout', methods=['POST'])
@current_user_required
def logout(current_user):
    return jsonify({
        'message': f'Logout realizado com sucesso para {current_user.username}'
    }), 200


@auth_bp.route('/change-password', methods=['POST'])
@limiter.limit('10 per hour')
@current_user_required
def change_password(current_user):
    data = request.get_json(silent=True) or {}
    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password:
        return jsonify({'error': 'Senha atual é obrigatória.'}), 400

    if not current_user.check_password(current_password):
        return jsonify({'error': 'Senha atual incorreta.'}), 400

    password_error = validate_password(new_password)
    if password_error:
        return jsonify({'error': password_error}), 400

    current_user.set_password(new_password)
    db.session.commit()
    # Tokens antigos deixam de valer após a troca; devolve um novo para a sessão atual.
    return jsonify({
        'message': 'Senha alterada com sucesso.',
        'access_token': issue_access_token(current_user),
        'user': current_user.to_dict(),
    }), 200
