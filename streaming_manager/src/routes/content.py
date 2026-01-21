from flask import Blueprint, request, jsonify
from src.models.content import Content, StreamingPlatform, ContentStreaming, db
from src.routes.auth import admin_required
from sqlalchemy import and_

content_bp = Blueprint('content', __name__)

@content_bp.route('/content', methods=['GET'])
def get_content():
    try:
        # Parâmetros de filtro
        content_type = request.args.get('type')
        streaming_ids = request.args.getlist('streaming_ids')
        genre = request.args.get('genre')
        search = request.args.get('search')
        show_inactive = request.args.get('show_inactive', 'false').lower() == 'true'
        
        # Query base
        query = Content.query
        
        # Filtrar por status ativo (padrão: mostrar apenas ativos)
        if not show_inactive:
            query = query.filter(Content.is_active == True)
        
        # Aplicar filtros
        if content_type:
            query = query.filter(Content.type == content_type)
        
        if genre:
            query = query.filter(Content.genre.ilike(f'%{genre}%'))
        
        if search:
            query = query.filter(Content.title.ilike(f'%{search}%'))
        
        if streaming_ids:
            # Filtrar por streamings específicos
            streaming_ids = [int(sid) for sid in streaming_ids if sid.isdigit()]
            query = query.join(ContentStreaming).filter(
                and_(
                    ContentStreaming.streaming_id.in_(streaming_ids),
                    ContentStreaming.available == True
                )
            ).distinct()
        
        # Ordenar por título
        content_list = query.order_by(Content.title).all()
        
        return jsonify([content.to_dict() for content in content_list])
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@content_bp.route('/content', methods=['POST'])
@admin_required
def create_content():
    try:
        data = request.get_json()
        
        # Validar dados obrigatórios
        if not data.get('title'):
            return jsonify({'error': 'Título é obrigatório'}), 400
        
        if not data.get('type') or data.get('type') not in ['movie', 'series', 'anime']:
            return jsonify({'error': 'Tipo deve ser movie, series ou anime'}), 400
        
        # Criar novo conteúdo
        content = Content(
            title=data.get('title'),
            year=data.get('year'),
            type=data.get('type'),
            genre=data.get('genre'),
            poster_url=data.get('poster_url')
        )
        
        db.session.add(content)
        db.session.commit()
        
        # Associar streamings se fornecidos
        streaming_ids = data.get('streaming_ids', [])
        for streaming_id in streaming_ids:
            content_streaming = ContentStreaming(
                content_id=content.id,
                streaming_id=streaming_id,
                available=True
            )
            db.session.add(content_streaming)
        
        db.session.commit()
        
        return jsonify(content.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@content_bp.route('/content/<int:content_id>', methods=['GET'])
def get_content_by_id(content_id):
    try:
        content = Content.query.get_or_404(content_id)
        return jsonify(content.to_dict())
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@content_bp.route('/content/<int:content_id>', methods=['PUT'])
@admin_required
def update_content(content_id):
    try:
        content = Content.query.get_or_404(content_id)
        data = request.get_json()
        
        # Atualizar campos
        if 'title' in data:
            content.title = data['title']
        if 'year' in data:
            content.year = data['year']
        if 'type' in data and data['type'] in ['movie', 'series', 'anime']:
            content.type = data['type']
        if 'genre' in data:
            content.genre = data['genre']
        if 'poster_url' in data:
            content.poster_url = data['poster_url']
        
        # Atualizar streamings se fornecidos
        if 'streaming_ids' in data:
            # Remover associações existentes
            ContentStreaming.query.filter_by(content_id=content_id).delete()
            
            # Adicionar novas associações
            for streaming_id in data['streaming_ids']:
                content_streaming = ContentStreaming(
                    content_id=content_id,
                    streaming_id=streaming_id,
                    available=True
                )
                db.session.add(content_streaming)
        
        db.session.commit()
        
        return jsonify(content.to_dict())
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@content_bp.route('/content/<int:content_id>', methods=['DELETE'])
@admin_required
def delete_content(content_id):
    try:
        content = Content.query.get_or_404(content_id)
        db.session.delete(content)
        db.session.commit()
        
        return jsonify({'message': 'Conteúdo removido com sucesso'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@content_bp.route('/content/<int:content_id>/toggle', methods=['PATCH'])
@admin_required
def toggle_content_active(content_id):
    try:
        content = Content.query.get_or_404(content_id)
        content.is_active = not content.is_active
        db.session.commit()
        
        status = 'ativado' if content.is_active else 'desativado'
        return jsonify({
            'message': f'Conteúdo {status} com sucesso',
            'is_active': content.is_active
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@content_bp.route('/content/stats', methods=['GET'])
def get_stats():
    try:
        # Contar apenas conteúdos ativos
        total_content = Content.query.filter_by(is_active=True).count()
        movies = Content.query.filter_by(type='movie', is_active=True).count()
        series = Content.query.filter_by(type='series', is_active=True).count()
        animes = Content.query.filter_by(type='anime', is_active=True).count()
        
        # Contar inativos
        total_inactive = Content.query.filter_by(is_active=False).count()
        
        # Estatísticas por streaming
        streaming_stats = []
        streamings = StreamingPlatform.query.filter_by(active=True).all()
        
        for streaming in streamings:
            count = db.session.query(ContentStreaming).join(Content).filter(
                ContentStreaming.streaming_id == streaming.id,
                ContentStreaming.available == True,
                Content.is_active == True
            ).count()
            
            streaming_stats.append({
                'streaming': streaming.to_dict(),
                'count': count
            })
        
        return jsonify({
            'total_content': total_content,
            'total_inactive': total_inactive,
            'by_type': {
                'movies': movies,
                'series': series,
                'animes': animes
            },
            'by_streaming': streaming_stats
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

