"""
Communications Engine Models

Provides a flexible, polymorphic system for managing email templates and 
scheduled communications for HR processes (Onboarding, Offboarding) with 
extensibility for future use cases like security bulletins and campaigns.
"""
from datetime import datetime
from ..extensions import db


class EmailTemplate(db.Model):
    """
    Reusable email templates with Jinja2 support for dynamic content.
    Templates can be categorized for filtering and organization.
    """
    __tablename__ = 'email_template'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    body_html = db.Column(db.Text, nullable=False)  # Jinja2 enabled
    category = db.Column(db.String(50), default='general')  # 'onboarding', 'offboarding', 'security_bulletin', 'general'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    pack_communications = db.relationship('PackCommunication', backref='template', lazy=True)
    scheduled_communications = db.relationship('ScheduledCommunication', backref='template', lazy=True)
    
    def __repr__(self):
        return f'<EmailTemplate {self.name}>'


class PackCommunication(db.Model):
    """
    Defines WHEN a communication should be sent relative to a process.
    Links an OnboardingPack to an EmailTemplate with timing rules.
    """
    __tablename__ = 'pack_communication'
    
    id = db.Column(db.Integer, primary_key=True)
    pack_id = db.Column(db.Integer, db.ForeignKey('onboarding_pack.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('email_template.id'), nullable=False)
    
    # Timing: offset in days from key date (start_date for onboarding, departure_date for offboarding)
    # Positive = after, Negative = before
    offset_days = db.Column(db.Integer, default=0)
    
    # Who receives this email
    # 'target_user' = the onboarding/offboarding user
    # 'personal_email' = external email (not implemented yet)
    # 'manager' = assigned manager
    # 'buddy' = assigned buddy
    recipient_type = db.Column(db.String(50), default='target_user')
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to pack - creates 'pack.communications' on OnboardingPack
    pack = db.relationship('OnboardingPack', backref=db.backref('communications', lazy=True))
    
    def __repr__(self):
        return f'<PackCommunication Pack:{self.pack_id} Template:{self.template_id} +{self.offset_days}d>'


class ScheduledCommunication(db.Model):
    """
    Execution record for a scheduled email.
    Uses polymorphic references to support different process types.
    """
    __tablename__ = 'scheduled_communication'
    
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('email_template.id'), nullable=False)
    
    # Status tracking
    status = db.Column(db.String(20), default='pending')  # 'pending', 'sent', 'failed', 'cancelled'
    scheduled_date = db.Column(db.Date, nullable=False)
    sent_at = db.Column(db.DateTime, nullable=True)
    
    # Polymorphic reference to the source process
    # target_type: 'onboarding', 'offboarding', or future types like 'security_campaign'
    target_type = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    
    # Cached recipient info - stored at creation time to avoid issues if user data changes
    recipient_email = db.Column(db.String(120), nullable=True)
    recipient_type = db.Column(db.String(50))  # 'target_user', 'manager', 'buddy'
    recipient_name = db.Column(db.String(100), nullable=True)
    
    # Error tracking for failed sends
    error_message = db.Column(db.Text, nullable=True)
    retry_count = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Indexes for efficient querying
    __table_args__ = (
        db.Index('idx_scheduled_comm_target', 'target_type', 'target_id'),
        db.Index('idx_scheduled_comm_status_date', 'status', 'scheduled_date'),
    )
    
    def __repr__(self):
        return f'<ScheduledCommunication {self.id} {self.target_type}:{self.target_id} {self.status}>'
    
    @property
    def is_overdue(self):
        """Check if this communication is past its scheduled date."""
        if self.status == 'pending':
            return self.scheduled_date < datetime.utcnow().date()
        return False
    
    def get_target_process(self):
        """Load and return the target process object."""
        from .onboarding import OnboardingProcess, OffboardingProcess
        
        if self.target_type == 'onboarding':
            return OnboardingProcess.query.get(self.target_id)
        elif self.target_type == 'offboarding':
            return OffboardingProcess.query.get(self.target_id)
        return None
