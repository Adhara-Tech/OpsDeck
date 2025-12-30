from datetime import datetime
from ..extensions import db

class RiskAssessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False) # e.g., "Q1 2024 Assessment"
    status = db.Column(db.String(50), default='Draft') # Draft, In Review, Locked
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    locked_at = db.Column(db.DateTime, nullable=True)
    
    # Snapshot of global metrics at closure time
    total_residual_risk = db.Column(db.Integer) 
    
    items = db.relationship('RiskAssessmentItem', backref='assessment', cascade='all, delete-orphan')

    @property
    def current_total_risk(self):
        """Calculates sum of residual scores for current items (dynamic)."""
        return sum(item.residual_score for item in self.items)

    def calculate_total_risk(self):
        """Saves the current total risk to the database field."""
        self.total_residual_risk = self.current_total_risk
        return self.total_residual_risk

class RiskAssessmentItem(db.Model):
    """
    Represents a risk at a specific point in time.
    IMPORTANT: Fields here are COPIES of live risk values.
    """
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('risk_assessment.id'), nullable=False)
    original_risk_id = db.Column(db.Integer, db.ForeignKey('risk.id'), nullable=True) # Optional link to original
    
    # Relationship to original risk for assessment history access
    original_risk = db.relationship('Risk', backref=db.backref('assessment_items', lazy='dynamic'))
    
    # --- SNAPSHOT DATA (Frozen values) ---
    risk_description = db.Column(db.Text)
    threat_type_name = db.Column(db.String(100)) # Copy of ThreatType name
    category_list = db.Column(db.String(255)) # Comma-separated categories
    
    # Scores
    inherent_impact = db.Column(db.Integer)
    inherent_likelihood = db.Column(db.Integer)
    residual_impact = db.Column(db.Integer)
    residual_likelihood = db.Column(db.Integer)
    
    treatment_strategy = db.Column(db.String(50))
    mitigation_notes = db.Column(db.Text) # Specific notes for this assessment

    # --- Relationships ---
    evidence = db.relationship('RiskAssessmentEvidence', backref='item', cascade='all, delete-orphan')

    @property
    def residual_score(self):
        return (self.residual_impact or 0) * (self.residual_likelihood or 0)

    @property
    def inherent_score(self):
        return (self.inherent_impact or 0) * (self.inherent_likelihood or 0)

class RiskAssessmentEvidence(db.Model):
    """
    Polymorphic table to link evidence (Policies, Assets, etc.) to an assessment item.
    Similar to AuditControlLink.
    """
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('risk_assessment_item.id'), nullable=False)
    
    linkable_type = db.Column(db.String(50), nullable=False)
    linkable_id = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text)

    @property
    def item_object(self):
        """Resolves the linked object dynamically."""
        from . import Policy, Asset, Documentation, Link, BCDRPlan
        
        model_map = {
            'Policy': Policy,
            'Asset': Asset,
            'Documentation': Documentation,
            'Link': Link,
            'BCDRPlan': BCDRPlan
        }
        
        model = model_map.get(self.linkable_type)
        if model:
            return model.query.get(self.linkable_id)
        return None
