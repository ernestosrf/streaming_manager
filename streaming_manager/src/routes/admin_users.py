from datetime import datetime
from flask import Blueprint, request, jsonify
from src.models.db import db
from src.models.user import (
    User,
    ROLE_ADMIN,
    STATUS_ACTIVE,
    STATUS_INACTIVE,
    STATUS_PENDING,
    STATUS_REJECTED,
    STATUSES,
)
from src.utils.auth import admin_required, issue_access_token
from src.utils.validators import validate_password

admin_users_bp = Blueprint('admin_users', __name__)

DEFAULT_PER_PAGE = 50
MAX_PER_PAGE = 200


def _user_or_404(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return None, (jsonify({'error': 'Usuário não encontrado.'}), 404)
    return user, None


@admin_users_bp.route('/users', methods=['GET'])
@admin_required
def list_users(current_user):
    search = (request.args.get('search') or '').strip()
    status = (request.args.get('status') or '').strip()

    query = User.query
    if search:
        query = query.filter(User.username.ilike(f'%{search}%'))
    if status:
        if status not in STATUSES:
            return jsonify({'error': 'Status inválido.'}), 400
        query = query.filter(User.status == status)

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', DEFAULT_PER_PAGE, type=int)
    if page < 1 or per_page < 1:
        return jsonify({'error': 'Paginação inválida.'}), 400
    per_page = min(per_page, MAX_PER_PAGE)

    total = query.count()
    users = (
        query.order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    response = jsonify([user.to_dict(include_private=True) for user in users])
    response.headers['X-Total-Count'] = str(total)
    return response


@admin_users_bp.route('/users/<int:user_id>/approve', methods=['POST'])
@admin_required
def approve_user(current_user, user_id):
    user, error = _user_or_404(user_id)
    if error:
        return error

    if user.role == ROLE_ADMIN:
        return jsonify({'error': 'A conta administrativa não pode ser alterada desta forma.'}), 400

    user.status = STATUS_ACTIVE
    if not user.approved_at:
        user.approved_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Usuário aprovado com sucesso.', 'user': user.to_dict(include_private=True)})


@admin_users_bp.route('/users/<int:user_id>/reject', methods=['POST'])
@admin_required
def reject_user(current_user, user_id):
    user, error = _user_or_404(user_id)
    if error:
        return error

    if user.role == ROLE_ADMIN:
        return jsonify({'error': 'A conta administrativa não pode ser rejeitada.'}), 400

    user.status = STATUS_REJECTED
    db.session.commit()
    return jsonify({'message': 'Usuário rejeitado.', 'user': user.to_dict(include_private=True)})


@admin_users_bp.route('/users/<int:user_id>/activate', methods=['POST'])
@admin_required
def activate_user(current_user, user_id):
    user, error = _user_or_404(user_id)
    if error:
        return error

    if user.role == ROLE_ADMIN:
        return jsonify({'error': 'A conta administrativa não pode ser alterada desta forma.'}), 400

    if user.status == STATUS_PENDING:
        return jsonify({'error': 'Contas pendentes devem ser aprovadas, não ativadas.'}), 400

    user.status = STATUS_ACTIVE
    if not user.approved_at:
        user.approved_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Usuário ativado com sucesso.', 'user': user.to_dict(include_private=True)})


@admin_users_bp.route('/users/<int:user_id>/deactivate', methods=['POST'])
@admin_required
def deactivate_user(current_user, user_id):
    user, error = _user_or_404(user_id)
    if error:
        return error

    if user.id == current_user.id:
        return jsonify({'error': 'Você não pode desativar a própria conta.'}), 400

    if user.role == ROLE_ADMIN:
        return jsonify({'error': 'A conta administrativa não pode ser desativada.'}), 400

    user.status = STATUS_INACTIVE
    db.session.commit()
    return jsonify({
        'message': 'Usuário desativado. A watchlist pública ficou indisponível.',
        'user': user.to_dict(include_private=True),
    })


@admin_users_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(current_user, user_id):
    user, error = _user_or_404(user_id)
    if error:
        return error

    if user.id == current_user.id:
        return jsonify({'error': 'Você não pode excluir a própria conta.'}), 400

    if user.role == ROLE_ADMIN:
        return jsonify({'error': 'A conta administrativa não pode ser excluída.'}), 400

    username = user.username
    db.session.delete(user)
    db.session.commit()
    return jsonify({
        'message': f'Conta "{username}" e todos os seus conteúdos foram removidos.',
    })


@admin_users_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_password(current_user, user_id):
    user, error = _user_or_404(user_id)
    if error:
        return error

    data = request.get_json(silent=True) or {}
    new_password = data.get('new_password')
    password_error = validate_password(new_password)
    if password_error:
        return jsonify({'error': password_error}), 400

    user.set_password(new_password)
    db.session.commit()
    payload = {'message': f'Senha de "{user.username}" redefinida com sucesso.'}
    if user.id == current_user.id:
        # A troca invalida o token atual do próprio administrador.
        payload['access_token'] = issue_access_token(user)
    return jsonify(payload)
