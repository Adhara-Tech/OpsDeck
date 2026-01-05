from datetime import datetime
from ..extensions import db

class Configuration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # Ownership (Polymorphic-like)
    owner_id = db.Column(db.Integer)
    owner_type = db.Column(db.String(50)) # 'User' or 'Group'
    
    # Links to other assets (Nullable FKs)
    service_id = db.Column(db.Integer, db.ForeignKey('business_service.id'), nullable=True)
    software_id = db.Column(db.Integer, db.ForeignKey('software.id'), nullable=True)
    license_id = db.Column(db.Integer, db.ForeignKey('license.id'), nullable=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=True)
    
    # Relationships
    versions = db.relationship('ConfigurationVersion', backref='configuration', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def latest_version(self):
        return self.versions.order_by(ConfigurationVersion.version_number.desc()).first()

class ConfigurationVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    configuration_id = db.Column(db.Integer, db.ForeignKey('configuration.id'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    commit_message = db.Column(db.String(255))
    
    created_by = db.relationship('User')
