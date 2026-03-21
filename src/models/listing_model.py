from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


# ── Listing ────────────────────────────────────────────────────────────────────
class Listing(db.Model):
    __tablename__ = 'listings'
    __table_args__ = (
        db.Index('ix_listing_category', 'category'),
        db.Index('ix_listing_provider', 'provider_id'),
        db.Index('ix_listing_location', 'latitude', 'longitude'),
        db.Index('ix_listing_verified', 'is_verified'),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.String(50))
    price_numeric = db.Column(db.Integer, default=0)  # numeric extracted for filtering
    contact = db.Column(db.String(50))
    address = db.Column(db.String(200))
    image_url = db.Column(db.String(300), nullable=True)

    keywords = db.Column(db.String(500), default="")

    provider_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_verified = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Float, default=0.0)

    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True, default=None)

    reviews = db.relationship('Review', backref='listing', lazy=True, cascade='all, delete-orphan')

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'category': self.category,
            'price': self.price,
            'price_numeric': self.price_numeric,
            'contact': self.contact,
            'address': self.address,
            'is_verified': self.is_verified,
            'rating': self.rating,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'keywords': self.keywords,
            'image_url': self.image_url,
            'provider_id': self.provider_id,
        }


# ── Review ─────────────────────────────────────────────────────────────────────
class Review(db.Model):
    __tablename__ = 'reviews'
    __table_args__ = (
        db.UniqueConstraint('listing_id', 'reviewer_id', name='uq_review_listing_user'),
    )

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listings.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ── Lead ───────────────────────────────────────────────────────────────────────
class Lead(db.Model):
    __tablename__ = 'leads'
    __table_args__ = (
        db.Index('ix_lead_provider', 'provider_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    customer_phone = db.Column(db.String(20), nullable=False)
    message = db.Column(db.String(200))
    status = db.Column(db.String(20), default="new")

    listing_id = db.Column(db.Integer, db.ForeignKey('listings.id'))
    provider_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'customer_phone': self.customer_phone,
            'status': self.status,
            'date': self.created_at.strftime("%Y-%m-%d %H:%M")
        }


# ── JobRequest ─────────────────────────────────────────────────────────────────
class JobRequest(db.Model):
    __tablename__ = 'job_requests'
    __table_args__ = (
        db.Index('ix_jobrequest_customer', 'customer_id'),
        db.Index('ix_jobrequest_status', 'status'),
    )

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100))
    status = db.Column(db.String(20), default="open")
    notifications_sent = db.Column(db.Integer, default=0)

    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    customer = db.relationship('src.models.user_model.User', backref='jobs')


# ── BotSession ─────────────────────────────────────────────────────────────────
class BotSession(db.Model):
    __tablename__ = 'bot_sessions'
    __table_args__ = (
        db.Index('ix_botsession_sender', 'sender_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.String(50), unique=True, nullable=False)
    history_json = db.Column(db.Text, default='[]')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
