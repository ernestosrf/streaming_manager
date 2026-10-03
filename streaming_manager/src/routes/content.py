from flask import Blueprint, request, jsonify, abort
from sqlalchemy import and_
from src.models.content import Content, StreamingPlatform, ContentStreaming
from src.models.db import db
from src.models.user import User, STATUS_ACTIVE
from src.utils.auth import current_user_required, get_admin_user
from flask_jwt_extended import jwt_required, get_jwt_identity

content_bp = Blueprint('content', __name__)

VALID_TYPES = ('movie', 'series', 'anime')


def _parse_year(value):
    if value is None or value == '':
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _apply_content_filters(query):
    content_type = request.args.get('type')
    streaming_ids = request.args.getlist('streaming_ids')
    genre = request.args.get('genre')
    search = request.args.get('search')

    if content_type:
        query = query.filter(Content.type == content_type)
    if genre:
        query = query.filter(Content.genre.ilike(f'%{genre}%'))
    if search:
        query = query.filter(Content.title.ilike(f'%{search}%'))
    if streaming_ids:
        streaming_ids = [int(sid) for sid in streaming_ids if sid.isdigit()]
        if streaming_ids:
            query = query.join(ContentStreaming).filter(
                and_(
                    ContentStreaming.streaming_id.in_(streaming_ids),
                    ContentStreaming.available == True  # noqa: E712
                )
            ).distinct()
    return query


def _can_see_inactive(owner):
    identity = get_jwt_identity()
    if identity is None or owner is None:
        return False
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return False
    return owner.id == user_id


def _watchlist_query(owner, show_inactive_requested):
    query = Content.query.filter(Content.owner_id == owner.id)
    if not (show_inactive_requested and _can_see_inactive(owner)):
        query = query.filter(Content.is_active == True)  # noqa: E712
    return _apply_content_filters(query)


def _watchlist_payload(owner):
    show_inactive = request.args.get('show_inactive', 'false').lower() == 'true'
    content_list = _watchlist_query(owner, show_inactive).order_by(Content.title).all()
    return {
        'owner': owner.to_dict(),
        'contents': [item.to_dict() for item in content_list],
    }


def _stats_for_owner(owner, include_inactive):
    base = Content.query.filter_by(owner_id=owner.id)
    active = base.filter_by(is_active=True)
    movies = active.filter_by(type='movie').count()
    series = active.filter_by(type='series').count()
    animes = active.filter_by(type='anime').count()
    total_inactive = base.filter_by(is_active=False).count() if include_inactive else 0

    streaming_stats = []
    streamings = StreamingPlatform.query.filter_by(active=True).all()
    for streaming in streamings:
        count = db.session.query(ContentStreaming).join(Content).filter(
            ContentStreaming.streaming_id == streaming.id,
            ContentStreaming.available == True,  # noqa: E712
            Content.is_active == True,  # noqa: E712
            Content.owner_id == owner.id,
        ).count()
        streaming_stats.append({
            'streaming': streaming.to_dict(),
            'count': count,
        })

    return {
        'total_content': active.count(),
        'total_inactive': total_inactive,
        'by_type': {
            'movies': movies,
            'series': series,
            'animes': animes,
        },
        'by_streaming': streaming_stats,
    }


def _public_owner_or_404(username):
    owner = User.query.filter_by(username=username).first()
    if not owner or owner.status != STATUS_ACTIVE:
        return None
    return owner


def _replace_streamings(content, streaming_ids):
    ContentStreaming.query.filter_by(content_id=content.id).delete()
    for streaming_id in streaming_ids:
        db.session.add(ContentStreaming(
            content_id=content.id,
            streaming_id=streaming_id,
            available=True,
        ))


def _get_or_404(model, ident):
    obj = db.session.get(model, ident)
    if obj is None:
        abort(404)
    return obj


def _owner_forbidden():
    return jsonify({'error': 'Você só pode alterar conteúdos da sua própria watchlist.'}), 403


@content_bp.route('/watchlists', methods=['GET'])
@jwt_required(optional=True)
def get_admin_watchlist():
    owner = get_admin_user()
    if not owner:
        return jsonify({'error': 'Watchlist principal não encontrada.'}), 404
    return jsonify(_watchlist_payload(owner))


@content_bp.route('/watchlists/<username>', methods=['GET'])
@jwt_required(optional=True)
def get_user_watchlist(username):
    owner = _public_owner_or_404(username)
    if not owner:
        return jsonify({'error': 'Watchlist não encontrada.'}), 404
    return jsonify(_watchlist_payload(owner))


@content_bp.route('/watchlists/<username>/stats', methods=['GET'])
@jwt_required(optional=True)
def get_user_watchlist_stats(username):
    admin = get_admin_user()
    if admin and username == admin.username:
        owner = admin
    else:
        owner = _public_owner_or_404(username)
        if not owner:
            return jsonify({'error': 'Watchlist não encontrada.'}), 404

    include_inactive = _can_see_inactive(owner)
    return jsonify(_stats_for_owner(owner, include_inactive))


@content_bp.route('/content', methods=['GET'])
@jwt_required(optional=True)
def get_content():
    """Catálogo público da watchlist principal (administrador)."""
    owner = get_admin_user()
    if not owner:
        return jsonify([])
    payload = _watchlist_payload(owner)
    return jsonify(payload['contents'])


@content_bp.route('/content/stats', methods=['GET'])
@jwt_required(optional=True)
def get_stats():
    owner = get_admin_user()
    if not owner:
        return jsonify({
            'total_content': 0,
            'total_inactive': 0,
            'by_type': {'movies': 0, 'series': 0, 'animes': 0},
            'by_streaming': [],
        })
    return jsonify(_stats_for_owner(owner, _can_see_inactive(owner)))


@content_bp.route('/content/suggestions', methods=['GET'])
@current_user_required
def suggest_content(current_user):
    query_text = (request.args.get('q') or '').strip()
    if len(query_text) < 2:
        return jsonify([])

    content_type = request.args.get('type')
    year = _parse_year(request.args.get('year'))

    query = Content.query.join(User).filter(
        User.status == STATUS_ACTIVE,
        Content.is_active == True,  # noqa: E712
        Content.title.ilike(f'%{query_text}%'),
    )

    if content_type in VALID_TYPES:
        query = query.filter(Content.type == content_type)
    if year is not None:
        query = query.filter(Content.year == year)

    matches = query.order_by(Content.title.asc(), Content.id.asc()).limit(50).all()

    seen = set()
    suggestions = []
    for item in matches:
        key = (item.title.strip().lower(), item.year, item.type)
        if key in seen:
            continue
        seen.add(key)
        suggestions.append(item.to_suggestion_dict())
        if len(suggestions) >= 8:
            break

    return jsonify(suggestions)


@content_bp.route('/content', methods=['POST'])
@current_user_required
def create_content(current_user):
    data = request.get_json(silent=True) or {}

    if not data.get('title'):
        return jsonify({'error': 'Título é obrigatório'}), 400

    if not data.get('type') or data.get('type') not in VALID_TYPES:
        return jsonify({'error': 'Tipo deve ser movie, series ou anime'}), 400

    try:
        content = Content(
            title=data.get('title'),
            year=_parse_year(data.get('year')),
            type=data.get('type'),
            genre=data.get('genre'),
            poster_url=data.get('poster_url'),
            owner_id=current_user.id,
        )
        db.session.add(content)
        db.session.flush()

        streaming_ids = data.get('streaming_ids', [])
        _replace_streamings(content, streaming_ids)
        db.session.commit()
        return jsonify(content.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@content_bp.route('/content/<int:content_id>', methods=['GET'])
@jwt_required(optional=True)
def get_content_by_id(content_id):
    content = _get_or_404(Content, content_id)
    owner = content.owner
    if not owner or owner.status != STATUS_ACTIVE:
        identity = get_jwt_identity()
        is_owner = False
        if identity is not None:
            try:
                is_owner = int(identity) == content.owner_id
            except (TypeError, ValueError):
                is_owner = False
        if not is_owner:
            return jsonify({'error': 'Conteúdo não encontrado.'}), 404

    if not content.is_active and not _can_see_inactive(owner):
        return jsonify({'error': 'Conteúdo não encontrado.'}), 404

    return jsonify(content.to_dict())


@content_bp.route('/content/<int:content_id>', methods=['PUT'])
@current_user_required
def update_content(current_user, content_id):
    content = _get_or_404(Content, content_id)
    if content.owner_id != current_user.id:
        return _owner_forbidden()

    data = request.get_json(silent=True) or {}
    try:
        if 'title' in data:
            content.title = data['title']
        if 'year' in data:
            content.year = _parse_year(data['year'])
        if 'type' in data and data['type'] in VALID_TYPES:
            content.type = data['type']
        if 'genre' in data:
            content.genre = data['genre']
        if 'poster_url' in data:
            content.poster_url = data['poster_url']
        if 'streaming_ids' in data:
            _replace_streamings(content, data['streaming_ids'])

        db.session.commit()
        return jsonify(content.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@content_bp.route('/content/<int:content_id>', methods=['DELETE'])
@current_user_required
def delete_content(current_user, content_id):
    content = _get_or_404(Content, content_id)
    if content.owner_id != current_user.id:
        return _owner_forbidden()

    try:
        db.session.delete(content)
        db.session.commit()
        return jsonify({'message': 'Conteúdo removido com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@content_bp.route('/content/<int:content_id>/toggle', methods=['PATCH'])
@current_user_required
def toggle_content_active(current_user, content_id):
    content = _get_or_404(Content, content_id)
    if content.owner_id != current_user.id:
        return _owner_forbidden()

    try:
        content.is_active = not content.is_active
        db.session.commit()
        status = 'ativado' if content.is_active else 'desativado'
        return jsonify({
            'message': f'Conteúdo {status} com sucesso',
            'is_active': content.is_active,
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
