from src.models.db import db
from src.utils.time import utcnow


SUGGESTION_FIELDS = ('id', 'title', 'year', 'type', 'genre', 'poster_url', 'streamings')


class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    year = db.Column(db.Integer, nullable=True)
    type = db.Column(db.String(20), nullable=False)  # 'movie', 'series', 'anime'
    genre = db.Column(db.String(100), nullable=True)
    poster_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    owner = db.relationship('User', back_populates='contents')
    streamings = db.relationship(
        'ContentStreaming',
        back_populates='content',
        cascade='all, delete-orphan',
    )

    def __repr__(self):
        return f'<Content {self.title} ({self.year})>'

    def to_dict(self, include_owner=False):
        data = {
            'id': self.id,
            'title': self.title,
            'year': self.year,
            'type': self.type,
            'genre': self.genre,
            'poster_url': self.poster_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'streamings': [
                cs.streaming_platform.to_dict()
                for cs in self.streamings
                if cs.available and cs.streaming_platform
            ],
        }
        if include_owner and self.owner:
            data['owner'] = {
                'id': self.owner.id,
                'username': self.owner.username,
            }
        return data

    def to_suggestion_dict(self):
        """Dados copiáveis para outra watchlist (sem status nem dono)."""
        data = self.to_dict()
        return {field: data[field] for field in SUGGESTION_FIELDS}


class StreamingPlatform(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    logo_url = db.Column(db.String(500), nullable=True)
    color = db.Column(db.String(7), nullable=True)
    active = db.Column(db.Boolean, default=True)

    contents = db.relationship(
        'ContentStreaming',
        back_populates='streaming_platform',
        cascade='all, delete-orphan',
    )

    def __repr__(self):
        return f'<StreamingPlatform {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'logo_url': self.logo_url,
            'color': self.color,
            'active': self.active,
        }


class ContentStreaming(db.Model):
    __tablename__ = 'content_streaming'

    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), primary_key=True)
    streaming_id = db.Column(db.Integer, db.ForeignKey('streaming_platform.id'), primary_key=True)
    available = db.Column(db.Boolean, default=True)
    last_checked = db.Column(db.DateTime, default=utcnow)

    content = db.relationship('Content', back_populates='streamings')
    streaming_platform = db.relationship('StreamingPlatform', back_populates='contents')

    def __repr__(self):
        return f'<ContentStreaming {self.content_id}-{self.streaming_id}>'

    def to_dict(self):
        return {
            'content_id': self.content_id,
            'streaming_id': self.streaming_id,
            'available': self.available,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None,
        }
