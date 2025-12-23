from datetime import datetime, date
from sqlalchemy.orm import foreign
from sqlalchemy import and_
from ..extensions import db
from .core import Attachment

# --- Association Tables for Security Activities ---

activity_participants = db.Table('activity_participants',
    db.Column('activity_id', db.Integer, db.ForeignKey('security_activity.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

activity_tags = db.Table('activity_tags',
    db.Column('activity_id', db.Integer, db.ForeignKey('security_activity.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

class ActivityRelatedObject(db.Model):
    """
    Polymorphic association table for linking SecurityActivity to other system objects
    (Software, Assets, Documentation, etc.)
    """
    __tablename__ = 'activity_related_object'
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('security_activity.id'), nullable=False)
    related_object_id = db.Column(db.Integer, nullable=False, index=True)
    related_object_type = db.Column(db.String(50), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship back to the activity
    activity = db.relationship('SecurityActivity', backref='related_object_links')
    
    @property
    def related_object(self):
        """Resolves the polymorphic relationship to the related object."""
        from .assets import Asset, Peripheral, Software, License
        from .procurement import Supplier, Subscription
        from .core import Link, Documentation
        from .policy import Policy
        from .training import Course
        from .bcdr import BCDRPlan
        from .security import SecurityIncident, Risk
        
        model_map = {
            'Asset': Asset,
            'Peripheral': Peripheral,
            'Software': Software,
            'License': License,
            'Supplier': Supplier,
            'Subscription': Subscription,
            'Link': Link,
            'Documentation': Documentation,
            'Policy': Policy,
            'Course': Course,
            'BCDRPlan': BCDRPlan,
            'SecurityIncident': SecurityIncident,
            'Risk': Risk,
        }
        
        model = model_map.get(self.related_object_type)
        if model:
            return model.query.get(self.related_object_id)
        return None

class SecurityActivity(db.Model):
    """
    Container for recurring security tasks (pentesting, access reviews, etc.)
    Follows the BCDRPlan pattern from bcdr.py
    """
    __tablename__ = 'security_activity'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    frequency = db.Column(db.String(50))  # 'monthly', 'quarterly', 'annual', etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Polymorphic owner (User or Group) - following Link pattern from core.py
    owner_id = db.Column(db.Integer)
    owner_type = db.Column(db.String(50))  # 'User' or 'Group'
    
    # Relationships
    
    # Many-to-Many: Participants (Users who participate in this activity)
    participants = db.relationship('User', secondary=activity_participants, backref='security_activities')
    
    # Many-to-Many: Tags
    tags = db.relationship('Tag', secondary=activity_tags, backref=db.backref('security_activities', lazy='dynamic'))
    
    # One-to-Many: Execution history
    executions = db.relationship('ActivityExecution', backref='activity', lazy='dynamic', 
                                cascade='all, delete-orphan', 
                                order_by='ActivityExecution.execution_date.desc()')
    
    # Polymorphic: Attachments
    attachments = db.relationship('Attachment',
                            primaryjoin="and_(SecurityActivity.id==foreign(Attachment.linkable_id), "
                                        "Attachment.linkable_type=='SecurityActivity')",
                            lazy=True, cascade='all, delete-orphan',
                            overlaps="attachments")
    
    # Polymorphic: Compliance Links (following pattern from security.py)
    compliance_links = db.relationship('ComplianceLink',
        primaryjoin=lambda: and_(
            foreign(__import__('src.models.security', fromlist=['ComplianceLink']).ComplianceLink.linkable_id) == SecurityActivity.id,
            __import__('src.models.security', fromlist=['ComplianceLink']).ComplianceLink.linkable_type == 'SecurityActivity'
        ),
        lazy='dynamic', cascade='all, delete-orphan',
        overlaps="compliance_links"
    )
    
    @property
    def owner(self):
        """Returns the User or Group object based on owner_type and owner_id."""
        from .auth import User, Group
        if self.owner_type == 'User' and self.owner_id:
            return User.query.get(self.owner_id)
        if self.owner_type == 'Group' and self.owner_id:
            return Group.query.get(self.owner_id)
        return None

class ActivityExecution(db.Model):
    """
    Execution record for a SecurityActivity
    Follows the BCDRTestLog pattern from bcdr.py
    """
    __tablename__ = 'activity_execution'
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('security_activity.id'), nullable=False)
    executor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    execution_date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(50), nullable=False)  # 'in_progress', 'success', 'failed', 'issue_detected'
    outcome_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    executor = db.relationship('User', foreign_keys=[executor_id])
    
    # Polymorphic: Attachments (for evidence files)
    attachments = db.relationship('Attachment',
                            primaryjoin="and_(ActivityExecution.id==foreign(Attachment.linkable_id), "
                                        "Attachment.linkable_type=='ActivityExecution')",
                            lazy=True, cascade='all, delete-orphan',
                            overlaps="attachments")
