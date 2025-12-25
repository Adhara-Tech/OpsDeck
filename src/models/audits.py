from datetime import datetime
from sqlalchemy import and_
from sqlalchemy.orm import foreign
from ..extensions import db
from .core import Attachment
from .security import Framework, FrameworkControl, ComplianceLink
from .crm import Contact
from .auth import User

# Association table for audit participants
audit_participants = db.Table('audit_participants',
    db.Column('audit_id', db.Integer, db.ForeignKey('compliance_audit.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class ComplianceAudit(db.Model):
    """
    Represents a snapshot of a Framework at a specific point in time for auditing purposes.
    Acts as a "Defense Platform" container.
    """
    __tablename__ = 'compliance_audit'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    
    # Status & Outcome
    status = db.Column(db.String(50), default='Planned', nullable=False) # Planned, Prep, Auditor Review, Closed
    outcome = db.Column(db.String(50)) # Pass, Fail, Qualified
    
    # Dates
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    framework_id = db.Column(db.Integer, db.ForeignKey('framework.id'), nullable=False)
    
    # External Auditor (Contact from CRM)
    auditor_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=True)
    
    # Internal Lead (User responsible for defense)
    internal_lead_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Relationships
    framework = db.relationship('Framework')
    auditor = db.relationship('Contact')
    internal_lead = db.relationship('User', foreign_keys=[internal_lead_id])
    
    participants = db.relationship('User', secondary=audit_participants, backref='audits_participating')
    
    audit_items = db.relationship(
        'AuditControlItem',
        backref='audit',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    # Polymorphic attachments (Proposal, Final Report, etc.)
    attachments = db.relationship(
        'Attachment',
        primaryjoin=lambda: and_(
            foreign(Attachment.linkable_id) == ComplianceAudit.id,
            Attachment.linkable_type == 'ComplianceAudit'
        ),
        lazy='dynamic',
        cascade='all, delete-orphan',
        overlaps="attachments"
    )

    @classmethod
    def create_snapshot(cls, framework_id, name, auditor_contact_id, internal_lead_id, copy_links=False):
        """
        Creates a new ComplianceAudit and snapshots all controls from the given framework.
        If copy_links is True, it also snapshots the evidence links.
        """
        # 1. Get the source Framework
        framework = Framework.query.get(framework_id)
        if not framework:
            raise ValueError(f"Framework with id {framework_id} not found")

        # 2. Create the ComplianceAudit instance
        audit = cls(
            name=name,
            framework_id=framework_id,
            auditor_id=auditor_contact_id,
            internal_lead_id=internal_lead_id,
            status='Planned'
        )
        db.session.add(audit)
        db.session.flush() # Flush to get the audit.id

        # 3. Iterate over controls and create AuditControlItem snapshots
        controls = framework.framework_controls.all()
        
        for control in controls:
            audit_item = AuditControlItem(
                audit_id=audit.id,
                original_control_id=control.id,
                
                # Snapshot fields (Copying values)
                control_code=control.control_id,
                control_title=control.name,
                control_description=control.description,
                
                # SOA defaults
                is_applicable=True,
                justification=None,
                
                # Audit defaults
                status='Compliant', # Default assumption, to be verified
            )
            db.session.add(audit_item)
            db.session.flush() # Need ID for links

            # 4. Copy Links if requested
            if copy_links:
                original_links = control.compliance_links.all()
                for link in original_links:
                    audit_link = AuditControlLink(
                        audit_item_id=audit_item.id,
                        linkable_type=link.linkable_type,
                        linkable_id=link.linkable_id,
                        description=link.description
                    )
                    db.session.add(audit_link)

        # 5. Commit transaction
        db.session.commit()
        
        return audit

class AuditControlItem(db.Model):
    """
    Represents a specific control within an audit. 
    Stores a snapshot of the original control text to preserve integrity.
    """
    __tablename__ = 'audit_control_item'

    id = db.Column(db.Integer, primary_key=True)
    audit_id = db.Column(db.Integer, db.ForeignKey('compliance_audit.id'), nullable=False)
    original_control_id = db.Column(db.Integer, db.ForeignKey('framework_control.id'), nullable=True)

    # --- Snapshot Fields (Copied from FrameworkControl) ---
    control_code = db.Column(db.String(100), nullable=False) # e.g. "A.5.1"
    control_title = db.Column(db.String(512), nullable=False)
    control_description = db.Column(db.Text)

    # --- SOA (Statement of Applicability) Fields ---
    is_applicable = db.Column(db.Boolean, default=True, nullable=False)
    justification = db.Column(db.Text) # For SOA
    
    # --- Defense & Findings ---
    internal_comments = db.Column(db.Text) # Private team chat/notes
    auditor_findings = db.Column(db.Text) # Notes from the auditor
    
    status = db.Column(db.String(50), default='Compliant', nullable=False) # Compliant, Gap, Observation

    # --- Relationships ---
    # audit relationship is defined in ComplianceAudit via backref
    original_control = db.relationship('FrameworkControl')

    # Linked Evidence (Snapshot of connections)
    linked_objects = db.relationship(
        'AuditControlLink',
        backref='audit_item',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    # Polymorphic attachments (Evidence files uploaded directly to this item)
    attachments = db.relationship(
        'Attachment',
        primaryjoin=lambda: and_(
            foreign(Attachment.linkable_id) == AuditControlItem.id,
            Attachment.linkable_type == 'AuditControlItem'
        ),
        lazy='dynamic',
        cascade='all, delete-orphan',
        overlaps="attachments"
    )

class AuditControlLink(db.Model):
    """
    Represents a link to an evidence object (Asset, Policy, etc.) specifically for this audit item.
    Allows the audit to have its own set of evidences, independent of the live framework.
    """
    __tablename__ = 'audit_control_link'

    id = db.Column(db.Integer, primary_key=True)
    audit_item_id = db.Column(db.Integer, db.ForeignKey('audit_control_item.id'), nullable=False)
    
    # Polymorphic Target
    linkable_type = db.Column(db.String(50), nullable=False)
    linkable_id = db.Column(db.Integer, nullable=False)
    
    description = db.Column(db.Text) # Context for why this is evidence

    @property
    def linked_object(self):
        """Resolves the polymorphic relationship to the linked object."""
        # Import models inside the method to avoid circular imports
        from .assets import Asset, Peripheral, Software, License, MaintenanceLog
        from .procurement import Supplier, Purchase, Budget, Subscription
        from .core import Link, Documentation
        from .policy import Policy
        from .training import Course
        from .bcdr import BCDRPlan
        from .security import SecurityIncident, SecurityAssessment, Risk, AssetInventory
        from .services import BusinessService
        
        # Map types to models
        model_map = {
            'Asset': Asset,
            'Peripheral': Peripheral,
            'Software': Software,
            'License': License,
            'MaintenanceLog': MaintenanceLog,
            'Supplier': Supplier,
            'Purchase': Purchase,
            'Budget': Budget,
            'Subscription': Subscription,
            'Link': Link,
            'Documentation': Documentation,
            'Policy': Policy,
            'Course': Course,
            'BCDRPlan': BCDRPlan,
            'SecurityIncident': SecurityIncident,
            'SecurityAssessment': SecurityAssessment,
            'Risk': Risk,
            'AssetInventory': AssetInventory,
            'BusinessService': BusinessService
        }
        
        model = model_map.get(self.linkable_type)
        if model:
            return model.query.get(self.linkable_id)
        return None
