from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from .user import db

class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    year = db.Column(db.Integer, nullable=True)
    type = db.Column(db.String(20), nullable=False)  # 'movie', 'series', 'anime'
    genre = db.Column(db.String(100), nullable=True)
    poster_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamento com streamings
    streamings = db.relationship('ContentStreaming', back_populates='content', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Content {self.title} ({self.year})>'

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'year': self.year,
            'type': self.type,
            'genre': self.genre,
            'poster_url': self.poster_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'streamings': [cs.streaming_platform.to_dict() for cs in self.streamings if cs.available]
        }

class StreamingPlatform(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    logo_url = db.Column(db.String(500), nullable=True)
    color = db.Column(db.String(7), nullable=True)  # Hex color
    active = db.Column(db.Boolean, default=True)
    
    # Relacionamento com conteúdos
    contents = db.relationship('ContentStreaming', back_populates='streaming_platform', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<StreamingPlatform {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'logo_url': self.logo_url,
            'color': self.color,
            'active': self.active
        }

class ContentStreaming(db.Model):
    __tablename__ = 'content_streaming'
    
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), primary_key=True)
    streaming_id = db.Column(db.Integer, db.ForeignKey('streaming_platform.id'), primary_key=True)
    available = db.Column(db.Boolean, default=True)
    last_checked = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    content = db.relationship('Content', back_populates='streamings')
    streaming_platform = db.relationship('StreamingPlatform', back_populates='contents')

    def __repr__(self):
        return f'<ContentStreaming {self.content_id}-{self.streaming_id}>'

    def to_dict(self):
        return {
            'content_id': self.content_id,
            'streaming_id': self.streaming_id,
            'available': self.available,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None
        }

