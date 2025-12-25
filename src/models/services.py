from datetime import datetime
from ..extensions import db
from sqlalchemy.orm import foreign
from sqlalchemy import and_

# Association table for self-referential Many-to-Many relationship (Dependencies)
service_dependencies = db.Table('service_dependencies',
    db.Column('parent_id', db.Integer, db.ForeignKey('business_service.id'), primary_key=True),
    db.Column('child_id', db.Integer, db.ForeignKey('business_service.id'), primary_key=True)
)

class BusinessService(db.Model):
    __tablename__ = 'business_service'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # Ownership
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship('User', foreign_keys=[owner_id])
    
    # Classification
    criticality = db.Column(db.String(50)) # 'Tier 1 - Critical', 'Tier 2 - High', 'Tier 3 - Standard'
    status = db.Column(db.String(50), default='Operational') # 'Pipeline', 'Operational', 'Retired'
    legacy_cost_center = db.Column(db.String(100))  # Preserved for migration
    cost_center_id = db.Column(db.Integer, db.ForeignKey('cost_center.id'), nullable=True)
    
    # SLAs
    sla_response_hours = db.Column(db.Integer)
    sla_resolution_hours = db.Column(db.Integer)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cost_center = db.relationship('CostCenter', backref='services')
    components = db.relationship('ServiceComponent', backref='service', lazy='dynamic', cascade='all, delete-orphan')
    documents = db.relationship('Documentation', secondary='service_documentation', backref='services')
    policies = db.relationship('Policy', secondary='service_policies', backref='services')
    activities = db.relationship('SecurityActivity', secondary='service_activities', backref='services')

    # Dependencies:
    # upstream_dependencies: Services I depend on.
    # downstream_dependencies: Services that depend on me.
    upstream_dependencies = db.relationship(
        'BusinessService',
        secondary=service_dependencies,
        primaryjoin=(id == service_dependencies.c.child_id),
        secondaryjoin=(id == service_dependencies.c.parent_id),
        backref=db.backref('downstream_dependencies', lazy='dynamic'),
        lazy='dynamic'
    )
    
    # Compliance Links
    compliance_links = db.relationship('ComplianceLink',
        primaryjoin=lambda: and_(
            foreign(__import__('src.models.security', fromlist=['ComplianceLink']).ComplianceLink.linkable_id) == BusinessService.id,
            __import__('src.models.security', fromlist=['ComplianceLink']).ComplianceLink.linkable_type == 'BusinessService'
        ),
        lazy='dynamic', cascade='all, delete-orphan',
        overlaps="compliance_links"
    )
    
    def __repr__(self):
        return f'<BusinessService {self.name}>'

class ServiceComponent(db.Model):
    """
    Polymorphic link to infrastructure components (Assets, Software, etc.)
    """
    __tablename__ = 'service_component'
    
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('business_service.id'), nullable=False)
    
    # Polymorphic fields
    component_type = db.Column(db.String(50), nullable=False) # 'Asset', 'Software', 'License', 'Supplier'
    component_id = db.Column(db.Integer, nullable=False)
    
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def linked_object(self):
        """Resolves the polymorphic relationship to the linked object."""
        # Import models inside the method to avoid circular imports
        from .assets import Asset, Peripheral, Software, License
        from .procurement import Supplier, Purchase, Subscription, Budget
        from .auth import User
        
        model_map = {
            'Asset': Asset,
            'Peripheral': Peripheral,
            'Software': Software,
            'License': License,
            'Supplier': Supplier,
            'Purchase': Purchase,
            'Subscription': Subscription,
            'Budget': Budget,
            'User': User
        }
        
        model = model_map.get(self.component_type)
        if model:
            return model.query.get(self.component_id)
        return None
