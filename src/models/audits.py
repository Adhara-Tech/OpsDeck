from datetime import datetime
from sqlalchemy import and_
from sqlalchemy.orm import foreign
from ..extensions import db
from .core import Attachment
from .security import Framework, FrameworkControl

class ComplianceAudit(db.Model):
    """
    Represents a snapshot of a Framework at a specific point in time for auditing purposes.
    """
    __tablename__ = 'compliance_audit'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    
    framework_id = db.Column(db.Integer, db.ForeignKey('framework.id'), nullable=False)
    auditor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    status = db.Column(db.String(50), default='Planned', nullable=False) # Planned, In Progress, Completed, Locked
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    framework = db.relationship('Framework')
    auditor = db.relationship('User')
    
    audit_items = db.relationship(
        'AuditControlItem',
        backref='audit',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    @classmethod
    def create_snapshot(cls, framework_id, name, auditor_id):
        """
        Creates a new ComplianceAudit and snapshots all controls from the given framework.
        """
        # 1. Get the source Framework
        framework = Framework.query.get(framework_id)
        if not framework:
            raise ValueError(f"Framework with id {framework_id} not found")

        # 2. Create the ComplianceAudit instance
        audit = cls(
            name=name,
            framework_id=framework_id,
            auditor_id=auditor_id,
            status='Planned'
        )
        db.session.add(audit)
        db.session.flush() # Flush to get the audit.id

        # 3. Iterate over controls and create AuditControlItem snapshots
        # Using framework.framework_controls which is a dynamic relationship
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
                status='Not Started',
                auditor_notes=None
            )
            db.session.add(audit_item)

        # 4. Commit transaction
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
    justification = db.Column(db.Text)

    # --- Audit Fields ---
    status = db.Column(db.String(50), default='Not Started', nullable=False) # Not Started, Compliant, Non-Compliant, Observation
    auditor_notes = db.Column(db.Text)

    # --- Relationships ---
    # audit relationship is defined in ComplianceAudit via backref
    original_control = db.relationship('FrameworkControl')

    # Polymorphic attachments
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
