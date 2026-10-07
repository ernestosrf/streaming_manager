from flask import Blueprint, request, jsonify
from sqlalchemy import and_, func, not_
from sqlalchemy.orm import selectinload
from src.models.content import Content, StreamingPlatform, ContentStreaming
from src.models.db import db
from src.models.user import User, STATUS_ACTIVE
from src.utils.auth import current_user_required, get_admin_user, get_user_from_jwt
from src.utils.responses import server_error
from src.utils.validators import VALID_CONTENT_TYPES, validate_content_payload
from flask_jwt_extended import jwt_required

content_bp = Blueprint('content', __name__)


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
    if owner is None:
        return False
    viewer = get_user_from_jwt()
    return viewer is not None and viewer.id == owner.id


def _with_streamings(query):
    """Carrega streamings e plataformas em lote, evitando N+1 no to_dict()."""
    return query.options(
        selectinload(Content.streamings).selectinload(ContentStreaming.streaming_platform)
    )


def _watchlist_query(owner, show_inactive_requested):
    query = _with_streamings(Content.query.filter(Content.owner_id == owner.id))
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
    active_by_type = {}
    total_inactive = 0
    rows = db.session.query(Content.is_active, Content.type, func.count(Content.id)).filter(
        Content.owner_id == owner.id,
    ).group_by(Content.is_active, Content.type).all()
    for is_active, content_type, count in rows:
        if is_active:
            active_by_type[content_type] = count
        else:
            total_inactive += count

    counts_by_streaming = dict(
        db.session.query(ContentStreaming.streaming_id, func.count()).join(Content).filter(
            ContentStreaming.available == True,  # noqa: E712
            Content.is_active == True,  # noqa: E712
            Content.owner_id == owner.id,
        ).group_by(ContentStreaming.streaming_id).all()
    )
    streamings = StreamingPlatform.query.filter_by(active=True).all()

    return {
        'total_content': sum(active_by_type.values()),
        'total_inactive': total_inactive if include_inactive else 0,
        'by_type': {
            'movies': active_by_type.get('movie', 0),
            'series': active_by_type.get('series', 0),
            'animes': active_by_type.get('anime', 0),
        },
        'by_streaming': [
            {'streaming': streaming.to_dict(), 'count': counts_by_streaming.get(streaming.id, 0)}
            for streaming in streamings
        ],
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


def _unknown_streaming_ids(streaming_ids):
    if not streaming_ids:
        return False
    found = StreamingPlatform.query.filter(StreamingPlatform.id.in_(streaming_ids)).count()
    return found != len(streaming_ids)


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

    query = _with_streamings(Content.query.join(User)).filter(
        User.status == STATUS_ACTIVE,
        Content.is_active == True,  # noqa: E712
        Content.title.ilike(f'%{query_text}%'),
    )

    if content_type in VALID_CONTENT_TYPES:
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
    fields, error = validate_content_payload(request.get_json(silent=True) or {})
    if error:
        return jsonify({'error': error}), 400

    streaming_ids = fields.pop('streaming_ids')
    if _unknown_streaming_ids(streaming_ids):
        return jsonify({'error': 'Streaming informado não existe.'}), 400

    try:
        content = Content(owner_id=current_user.id, **fields)
        db.session.add(content)
        db.session.flush()

        _replace_streamings(content, streaming_ids)
        db.session.commit()
        return jsonify(content.to_dict()), 201
    except Exception:
        db.session.rollback()
        return server_error('criar conteúdo')


@content_bp.route('/content/<int:content_id>', methods=['GET'])
@jwt_required(optional=True)
def get_content_by_id(content_id):
    content = db.get_or_404(Content, content_id)
    owner = content.owner
    is_owner = _can_see_inactive(owner)
    owner_is_public = owner is not None and owner.status == STATUS_ACTIVE
    if not is_owner and (not owner_is_public or not content.is_active):
        return jsonify({'error': 'Conteúdo não encontrado.'}), 404

    return jsonify(content.to_dict())


@content_bp.route('/content/<int:content_id>', methods=['PUT'])
@current_user_required
def update_content(current_user, content_id):
    content = db.get_or_404(Content, content_id)
    if content.owner_id != current_user.id:
        return _owner_forbidden()

    fields, error = validate_content_payload(request.get_json(silent=True) or {}, partial=True)
    if error:
        return jsonify({'error': error}), 400

    streaming_ids = fields.pop('streaming_ids', None)
    if streaming_ids is not None and _unknown_streaming_ids(streaming_ids):
        return jsonify({'error': 'Streaming informado não existe.'}), 400

    try:
        for field, value in fields.items():
            setattr(content, field, value)
        if streaming_ids is not None:
            _replace_streamings(content, streaming_ids)

        db.session.commit()
        return jsonify(content.to_dict())
    except Exception:
        db.session.rollback()
        return server_error('atualizar conteúdo')


@content_bp.route('/content/<int:content_id>', methods=['DELETE'])
@current_user_required
def delete_content(current_user, content_id):
    content = db.get_or_404(Content, content_id)
    if content.owner_id != current_user.id:
        return _owner_forbidden()

    try:
        db.session.delete(content)
        db.session.commit()
        return jsonify({'message': 'Conteúdo removido com sucesso'})
    except Exception:
        db.session.rollback()
        return server_error('remover conteúdo')


@content_bp.route('/content/<int:content_id>/toggle', methods=['PATCH'])
@current_user_required
def toggle_content_active(current_user, content_id):
    content = db.get_or_404(Content, content_id)
    if content.owner_id != current_user.id:
        return _owner_forbidden()

    data = request.get_json(silent=True) or {}
    target = data.get('is_active')
    if target is not None and not isinstance(target, bool):
        return jsonify({'error': 'is_active deve ser booleano.'}), 400

    try:
        # Com is_active explícito a operação é idempotente; sem ele, a inversão é feita
        # atomicamente no banco para que cliques concorrentes não se anulem.
        new_value = target if target is not None else not_(Content.is_active)
        Content.query.filter_by(id=content.id).update(
            {Content.is_active: new_value},
            synchronize_session=False,
        )
        db.session.commit()
        db.session.refresh(content)
        status = 'ativado' if content.is_active else 'desativado'
        return jsonify({
            'message': f'Conteúdo {status} com sucesso',
            'is_active': content.is_active,
        })
    except Exception:
        db.session.rollback()
        return server_error('alterar status do conteúdo')
