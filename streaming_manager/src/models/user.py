from werkzeug.security import generate_password_hash, check_password_hash
from src.models.db import db
from src.utils.time import utcnow

ROLE_ADMIN = 'admin'
ROLE_USER = 'user'
ROLES = (ROLE_ADMIN, ROLE_USER)

STATUS_PENDING = 'pending'
STATUS_ACTIVE = 'active'
STATUS_INACTIVE = 'inactive'
STATUS_REJECTED = 'rejected'
STATUSES = (STATUS_PENDING, STATUS_ACTIVE, STATUS_INACTIVE, STATUS_REJECTED)


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_USER)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    approved_at = db.Column(db.DateTime, nullable=True)

    contents = db.relationship(
        'Content',
        back_populates='owner',
        cascade='all, delete-orphan',
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == ROLE_ADMIN

    def is_active_account(self):
        return self.status == STATUS_ACTIVE

    def to_dict(self, include_private=False):
        data = {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'status': self.status,
        }
        if include_private:
            data['created_at'] = self.created_at.isoformat() if self.created_at else None
            data['approved_at'] = self.approved_at.isoformat() if self.approved_at else None
        return data

    def __repr__(self):
        return f'<User {self.username}>'
