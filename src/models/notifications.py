"""
Notification Event Configuration Model

Maps system events (like license expiry, subscription renewal) to email templates,
allowing admins to configure which notifications are enabled and which templates to use.
"""
from datetime import datetime
from ..extensions import db


class NotificationEvent(db.Model):
    """
    Maps system events to email templates for centralized notification management.
    Allows admins to enable/disable specific notifications and change templates.
    """
    __tablename__ = 'notification_event'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Event identification
    event_code = db.Column(db.String(50), unique=True, nullable=False)  # e.g., 'LICENSE_EXPIRING'
    name = db.Column(db.String(100), nullable=False)  # Human-readable name
    description = db.Column(db.Text)  # Explanation of when this event triggers
    
    # Link to the email template to use
    template_id = db.Column(db.Integer, db.ForeignKey('email_template.id'), nullable=True)
    template = db.relationship('EmailTemplate', backref='notification_events')
    
    # Control switches
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    
    # Optional: days before event to trigger (for expiry-type events)
    # Positive = days before, e.g., 7 means "7 days before expiry"
    days_offset = db.Column(db.Integer, default=7)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<NotificationEvent {self.event_code}>'
