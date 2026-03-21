from src.models.listing_model import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=True)
    role = db.Column(db.String(20), default='customer')  # 'customer', 'provider', 'admin'
    profile_image = db.Column(db.String(300), nullable=True)

    password_hash = db.Column(db.String(128))

    is_active_user = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True, default=None)

    listings = db.relationship('Listing', backref='provider', lazy=True)

    def set_password(self, password):
        """Encrypts the password before saving."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Checks if the password matches the hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.is_active_user and self.deleted_at is None

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def __repr__(self):
        return f"<User {self.name} ({self.role})>"