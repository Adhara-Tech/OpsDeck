# src/schemas.py
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from .extensions import db
from .models import User, Asset, Peripheral, License, Subscription
from .models.services import BusinessService

# --- Base Schema ---
class BaseSchema(SQLAlchemyAutoSchema):
    class Meta:
        sqla_session = db.session
        load_instance = True
        include_fk = True # Include foreign keys like user_id, asset_id

# --- Resource Schemas ---

class UserSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = User
        # Exclude sensitive data automatically
        exclude = ('password_hash', 'api_token') 

class AssetSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = Asset

class PeripheralSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = Peripheral

class LicenseSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = License

class SubscriptionSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = Subscription

class ServiceSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = BusinessService
        # Exclude complex recursive relationships to keep it light for now
        exclude = ('upstream_dependencies', 'downstream_dependencies', 'components')