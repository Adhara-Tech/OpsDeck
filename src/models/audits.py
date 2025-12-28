from datetime import datetime
from sqlalchemy import and_
from sqlalchemy.orm import foreign
from ..extensions import db
from .core import Attachment
from .security import Framework
from .onboarding import OnboardingProcess, OffboardingProcess

# Association table for audit participants
audit_participants = db.Table('audit_participants',
    db.Column('audit_id', db.Integer, db.ForeignKey('compliance_audit.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

# Association table for linking audits to onboarding/offboarding processes (Evidence)
audit_evidence = db.Table('audit_evidence',
    db.Column('audit_id', db.Integer, db.ForeignKey('compliance_audit.id'), primary_key=True),
    db.Column('onboarding_id', db.Integer, db.ForeignKey('onboarding_process.id'), nullable=True),
    db.Column('offboarding_id', db.Integer, db.ForeignKey('offboarding_process.id'), nullable=True)
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
    locked_at = db.Column(db.DateTime, nullable=True)

    @property
    def is_locked(self):
        return self.locked_at is not None

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
    
    onboardings = db.relationship('OnboardingProcess', secondary=audit_evidence, backref=db.backref('audits', overlaps="audits,onboardings,offboardings"), overlaps="audits,offboardings")
    offboardings = db.relationship('OffboardingProcess', secondary=audit_evidence, backref=db.backref('audits', overlaps="audits,onboardings,offboardings"), overlaps="audits,onboardings")
    
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
                status='Pending', # Starting state, to be assessed
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


    @classmethod
    def clone(cls, source_id, new_owner_id, target_date):
        """
        Clones an existing audit for a new period (Rollover).
        - Preserves: SOA (is_applicable), Justifications, Comments, Evidence Links.
        - Resets: Status (Compliant/Gap -> Pending), Dates, Auditor.
        - Metadata: New Name = "Renewal [Year]: [Old Name]", Owner = new_owner_id.
        """
        source = cls.query.get(source_id)
        if not source:
             raise ValueError(f"Source audit with id {source_id} not found")

        # 1. Create New Audit Header
        year = target_date.year if target_date else datetime.utcnow().year
        new_audit = cls(
            name=f"Renewal {year}: {source.name}",
            framework_id=source.framework_id,
            internal_lead_id=new_owner_id,
            # Reset dates and auditor
            auditor_id=None,
            start_date=None,
            end_date=target_date, # Use target_date as end_date deadline
            status='Planned',
            outcome=None,
            locked_at=None
        )
        db.session.add(new_audit)
        db.session.flush() # Generate ID

        # 2. Clone Controls
        # Iterate over source items to carry over decisions + evidence
        for old_item in source.audit_items:
            new_item = AuditControlItem(
                audit_id=new_audit.id,
                original_control_id=old_item.original_control_id,
                
                # --- SNAPSHOT TEXT ---
                # We copy from the OLD item to preserve the snapshot state 
                # (unless we want to re-sync with framework, but requirement says "Preserve")
                control_code=old_item.control_code,
                control_title=old_item.control_title,
                control_description=old_item.control_description,

                # --- COPY TEXT DATA ---
                justification=old_item.justification,
                internal_comments=old_item.internal_comments,
                
                # --- SOA LOGIC ---
                is_applicable=old_item.is_applicable
            )
            
            # --- STATUS RESET LOGIC ---
            if not old_item.is_applicable:
                new_item.status = 'Not Applicable' # Explicit string
            else:
                new_item.status = 'Pending' # Reset to Pending for re-validation

            db.session.add(new_item)
            db.session.flush() # Need ID for links
            
            # --- CLONE EVIDENCES (Reference Copy) ---
            # We copy the LINKS (pointers to assets/docs), not the attachments themselves (files)
            # Logic: "We used Policy X last year, we likely use it this year too"
            for link in old_item.linked_objects:
                 new_link = AuditControlLink(
                     audit_item_id=new_item.id,
                     linkable_type=link.linkable_type,
                     linkable_id=link.linkable_id,
                     description=link.description
                 )
                 db.session.add(new_link)

        db.session.commit()
        return new_audit

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
    
    status = db.Column(db.String(50), default='Pending', nullable=False) # Pending, Compliant, Observation, Gap, Not Applicable

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
    def display_name(self):
        """Devuelve el nombre legible del objeto, sin importar su tipo."""
        obj = self.linked_object
        if not obj:
            return "Elemento no encontrado"
        
        # 1. Políticas y Cursos usan 'title'
        if hasattr(obj, 'title'):
            return obj.title
            
        # 2. Riesgos usan 'risk_description'
        if hasattr(obj, 'risk_description'):
            # Opcional: Truncar si es muy largo, ya que suelen ser textos
            return obj.risk_description 

        # 3. Procesos de Onboarding
        if self.linkable_type == 'Onboarding':
            return f"Onboarding: {obj.new_hire_name or (obj.user.name if obj.user else 'Unknown')}"

        # 4. Procesos de Offboarding
        if self.linkable_type == 'Offboarding':
            return f"Offboarding: {obj.user.name if obj.user else 'Unknown'}"
            
        # 5. El resto (Assets, Users, etc.) usan 'name'
        return getattr(obj, 'name', str(obj))
    
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
        from .onboarding import OnboardingProcess, OffboardingProcess
        
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
            'BusinessService': BusinessService,
            'Onboarding': OnboardingProcess,
            'Offboarding': OffboardingProcess
        }
        
        model = model_map.get(self.linkable_type)
        if model:
            return model.query.get(self.linkable_id)
        return None
