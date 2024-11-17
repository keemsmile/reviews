from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy.dialects.sqlite import JSON

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'platform_admin' or 'business_admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=True)

    # Relationships
    business = db.relationship('Business', back_populates='users')

class Business(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    branding_color = db.Column(db.String(7), default="#007bff")  # Hex color code
    logo_url = db.Column(db.String(200))
    
    # Relationships
    users = db.relationship('User', back_populates='business')
    reviews = db.relationship('Review', back_populates='business')

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=True)
    customer_name = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='new')  # new, read, responded
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    
    # New fields
    sentiment = db.Column(db.String(20), nullable=True)  # positive, negative, neutral
    source = db.Column(db.String(50), nullable=True)  # google, yelp, direct, etc.
    contact_info = db.Column(JSON, nullable=True)  # Stores contact details as JSON
    improvement_feedback = db.Column(db.Text, nullable=True)
    tags = db.Column(JSON, nullable=True)  # Stores tags as JSON array
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    
    # Relationships
    business = db.relationship('Business', back_populates='reviews')
    response = db.relationship('ReviewResponse', back_populates='review', uselist=False)

class ReviewResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    review_id = db.Column(db.Integer, db.ForeignKey('review.id'), nullable=False)
    responder_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    review = db.relationship('Review', back_populates='response')
    responder = db.relationship('User')
