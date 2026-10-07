from flask import Blueprint, request, jsonify, abort
from sqlalchemy.exc import IntegrityError
from src.models.content import StreamingPlatform, db
from src.utils.auth import admin_required
from src.utils.responses import server_error

streaming_bp = Blueprint('streaming', __name__)


def _get_or_404(model, ident):
    obj = db.session.get(model, ident)
    if obj is None:
        abort(404)
    return obj


@streaming_bp.route('/streamings', methods=['GET'])
def get_streamings():
    try:
        active_only = request.args.get('active_only', 'true').lower() == 'true'

        query = StreamingPlatform.query
        if active_only:
            query = query.filter_by(active=True)

        streamings = query.order_by(StreamingPlatform.name).all()
        return jsonify([streaming.to_dict() for streaming in streamings])
    except Exception:
        return server_error('listar streamings')


@streaming_bp.route('/streamings', methods=['POST'])
@admin_required
def create_streaming(current_user):
    try:
        data = request.get_json(silent=True) or {}

        if not data.get('name'):
            return jsonify({'error': 'Nome é obrigatório'}), 400

        existing = StreamingPlatform.query.filter_by(name=data['name']).first()
        if existing:
            return jsonify({'error': 'Streaming já existe'}), 400

        streaming = StreamingPlatform(
            name=data['name'],
            logo_url=data.get('logo_url'),
            color=data.get('color'),
            active=data.get('active', True),
        )
        db.session.add(streaming)
        db.session.commit()
        return jsonify(streaming.to_dict()), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Streaming já existe'}), 400
    except Exception:
        db.session.rollback()
        return server_error('criar streaming')


@streaming_bp.route('/streamings/<int:streaming_id>', methods=['PUT'])
@admin_required
def update_streaming(current_user, streaming_id):
    try:
        streaming = _get_or_404(StreamingPlatform, streaming_id)
        data = request.get_json(silent=True) or {}

        if 'name' in data:
            streaming.name = data['name']
        if 'logo_url' in data:
            streaming.logo_url = data['logo_url']
        if 'color' in data:
            streaming.color = data['color']
        if 'active' in data:
            streaming.active = data['active']

        db.session.commit()
        return jsonify(streaming.to_dict())
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Streaming já existe'}), 400
    except Exception:
        db.session.rollback()
        return server_error('atualizar streaming')


@streaming_bp.route('/streamings/<int:streaming_id>', methods=['DELETE'])
@admin_required
def delete_streaming(current_user, streaming_id):
    try:
        streaming = _get_or_404(StreamingPlatform, streaming_id)
        db.session.delete(streaming)
        db.session.commit()
        return jsonify({'message': 'Streaming removido com sucesso'})
    except Exception:
        db.session.rollback()
        return server_error('remover streaming')
