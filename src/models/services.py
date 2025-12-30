from datetime import datetime
from ..extensions import db
from sqlalchemy.orm import foreign
from sqlalchemy import and_

# Association table for self-referential Many-to-Many relationship (Dependencies)
service_dependencies = db.Table('service_dependencies',
    db.Column('parent_id', db.Integer, db.ForeignKey('business_service.id'), primary_key=True),
    db.Column('child_id', db.Integer, db.ForeignKey('business_service.id'), primary_key=True)
)

# Association table for User Access (M2M)
service_users = db.Table('service_users',
    db.Column('service_id', db.Integer, db.ForeignKey('business_service.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class BusinessService(db.Model):
    __tablename__ = 'business_service'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default='Business Service') # 'Application', 'Business Service', 'Infrastructure', 'Capability'
    
    # Ownership
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship('User', foreign_keys=[owner_id])
    
    # User Access (New)
    users = db.relationship('User', secondary=service_users, backref='access_services')

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

    @property
    def aggregated_risk_score(self):
        """
        Calcula el riesgo máximo heredado de sus componentes de infraestructura.
        Si un componente tiene un max_risk_score alto, el servicio lo hereda.
        """
        max_score = 0
        
        # Revisar Componentes (Infraestructura)
        for comp in self.components:
            linked_obj = comp.linked_object
            # Verificamos si el objeto tiene la propiedad 'max_risk_score' (como Asset)
            if linked_obj and hasattr(linked_obj, 'max_risk_score'):
                score = linked_obj.max_risk_score
                if score and score > max_score:
                    max_score = score
        
        return max_score

    @property
    def risk_status_color(self):
        """Devuelve el color semántico para la UI/Gráficos basado en el riesgo."""
        score = self.aggregated_risk_score
        if score >= 20: return '#dc3545'  # Danger (Red)
        if score >= 12: return '#fd7e14'  # Orange
        if score >= 5:  return '#ffc107'  # Warning (Yellow)
        return '#198754'  # Success (Green)

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
