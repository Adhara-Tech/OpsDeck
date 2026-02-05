from datetime import datetime
from src.utils.timezone_helper import now
from ..extensions import db

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(255), nullable=False)
    contact_name = db.Column(db.String(255))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    status = db.Column(db.String(50), default='New') # New, Contacted, Qualified, Converted, Disqualified
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: now())

class Opportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50), default='Evaluating') # e.g., Evaluating, PoC, Negotiating, Won, Lost
    potential_value = db.Column(db.Float)
    currency = db.Column(db.String(3), default='EUR')
    estimated_close_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: now())
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    primary_contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'))

    # Relationships
    activities = db.relationship('Activity', backref='opportunity', lazy=True, cascade='all, delete-orphan', order_by='Activity.activity_date.desc()')

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False, default='Meeting') # e.g., Meeting, Call, Email
    activity_date = db.Column(db.DateTime, default=lambda: now())
    notes = db.Column(db.Text, nullable=False)

    # Relationship
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunity.id'), nullable=False)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    role = db.Column(db.String(50))
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: now())
    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    opportunities = db.relationship('Opportunity', backref='primary_contact', foreign_keys='Opportunity.primary_contact_id')
