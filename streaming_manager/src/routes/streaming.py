from flask import Blueprint, request, jsonify
from src.models.content import StreamingPlatform, db
from src.routes.auth import admin_required

streaming_bp = Blueprint('streaming', __name__)

@streaming_bp.route('/streamings', methods=['GET'])
def get_streamings():
    try:
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        
        query = StreamingPlatform.query
        if active_only:
            query = query.filter_by(active=True)
        
        streamings = query.order_by(StreamingPlatform.name).all()
        
        return jsonify([streaming.to_dict() for streaming in streamings])
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@streaming_bp.route('/streamings', methods=['POST'])
@admin_required
def create_streaming():
    try:
        data = request.get_json()
        
        # Validar dados obrigatórios
        if not data.get('name'):
            return jsonify({'error': 'Nome é obrigatório'}), 400
        
        # Verificar se já existe
        existing = StreamingPlatform.query.filter_by(name=data['name']).first()
        if existing:
            return jsonify({'error': 'Streaming já existe'}), 400
        
        # Criar novo streaming
        streaming = StreamingPlatform(
            name=data['name'],
            logo_url=data.get('logo_url'),
            color=data.get('color'),
            active=data.get('active', True)
        )
        
        db.session.add(streaming)
        db.session.commit()
        
        return jsonify(streaming.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@streaming_bp.route('/streamings/<int:streaming_id>', methods=['PUT'])
@admin_required
def update_streaming(streaming_id):
    try:
        streaming = StreamingPlatform.query.get_or_404(streaming_id)
        data = request.get_json()
        
        # Atualizar campos
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
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@streaming_bp.route('/streamings/<int:streaming_id>', methods=['DELETE'])
@admin_required
def delete_streaming(streaming_id):
    try:
        streaming = StreamingPlatform.query.get_or_404(streaming_id)
        db.session.delete(streaming)
        db.session.commit()
        
        return jsonify({'message': 'Streaming removido com sucesso'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

