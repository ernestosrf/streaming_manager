import os
from datetime import datetime

from src.models.db import db
from src.models.user import User, ROLE_ADMIN, STATUS_ACTIVE
from src.models.content import Content
from src.utils.validators import validate_password, validate_username


def seed_admin_and_assign_existing_content():
    """Cria o admin inicial a partir do ambiente e vincula conteúdos sem dono."""
    admin = User.query.filter_by(role=ROLE_ADMIN).order_by(User.id.asc()).first()
    if admin is None:
        username = (os.environ.get('ADMIN_USERNAME') or '').strip()
        password = os.environ.get('ADMIN_PASSWORD') or ''

        username_error = validate_username(username, allow_reserved=True)
        if username_error:
            raise RuntimeError(
                'ADMIN_USERNAME é obrigatório na primeira migração e deve ter 3 a 30 '
                f'caracteres (minúsculas, números e hífen). Detalhe: {username_error}'
            )

        password_error = validate_password(password)
        if password_error:
            raise RuntimeError(
                'ADMIN_PASSWORD é obrigatória na primeira migração e deve ter no mínimo 8 caracteres.'
            )

        if User.query.filter_by(username=username).first():
            raise RuntimeError(f'O username "{username}" já está em uso.')

        now = datetime.utcnow()
        admin = User(
            username=username,
            role=ROLE_ADMIN,
            status=STATUS_ACTIVE,
            created_at=now,
            approved_at=now,
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.flush()

    Content.query.filter(Content.owner_id.is_(None)).update(
        {Content.owner_id: admin.id},
        synchronize_session=False,
    )
    db.session.commit()
    return admin
