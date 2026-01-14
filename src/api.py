# src/api.py
from flask import request, current_app, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from .models import User, Asset, Peripheral, License, Subscription
from .models.services import BusinessService
from .schemas import (
    UserSchema, AssetSchema, PeripheralSchema, 
    LicenseSchema, SubscriptionSchema, ServiceSchema
)

# Define Blueprints for each resource
api_bp = Blueprint('api', 'api', url_prefix='/api/v1', description='OpsDeck API')

# --- Security Hook ---
@api_bp.before_request
def check_token():
    # Handle OPTIONS requests (for CORS/Preflight) if needed, usually flask handles it.
    if request.method == "OPTIONS":
        return None
        
    token = None
    # Check standard Authorization header
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization']
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        # Check if it's the schema/swagger endpoint? 
        # flask-smorest serves swagger at /swagger-ui (configured in init) and openapi.json at /openapi.json (root usually).
        # Our bp prefix is /api/v1. So swagger docs should be safe.
        current_app.logger.warning(
            "API Access Failed: Missing Token",
            extra={
                "event.action": "api.request.failure",
                "failure.reason": "missing_token",
                "source.ip": request.remote_addr,
                "http.request.method": request.method,
                "url.path": request.path
            }
        )
        return jsonify({"error": "Token is missing"}), 401
    
    current_api_user = User.query.filter_by(api_token=token).first()
    if not current_api_user:
        current_app.logger.warning(
            "API Access Failed: Invalid Token",
            extra={
                "event.action": "api.request.failure",
                "failure.reason": "invalid_token",
                "source.ip": request.remote_addr,
                "http.request.method": request.method,
                "url.path": request.path
            }
        )
        return jsonify({"error": "Token is invalid"}), 401

    # Log Success (Optional: might be verbose, maybe log only critical actions or sample)
    # For now, logging all authenticated API requests as requested.
    current_app.logger.info(
        f"API Access: {current_api_user.email}",
        extra={
            "event.action": "api.request.success",
            "user.id": current_api_user.id,
            "user.email": current_api_user.email,
            "source.ip": request.remote_addr,
            "http.request.method": request.method,
            "url.path": request.path
        }
    )

# --- Helper to register Read-Only routes ---
def register_read_only_resource(blueprint, model, schema, url_name):
    """
    Registers List (GET /) and Detail (GET /{id}) routes for a given model.
    """
    
    @blueprint.route(f'/{url_name}')
    class ListResource(MethodView):
        @blueprint.doc(security=[{"bearerAuth": []}])
        @blueprint.response(200, schema(many=True))
        # @blueprint.paginate(Page) # Disabled due to injection issue
        def get(self):
            """List all {url_name} (Protected)"""
            # Manual Pagination Fallback
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('page_size', 10, type=int)
            
            # Use SQLAlchemy pagination but return only items list
            # flask-smorest will serialize the list
            pagination = model.query.paginate(page=page, per_page=per_page, error_out=False)
            
            # Optional: We could set response headers for total count if needed
            # headers = {'X-Total-Count': str(pagination.total)}
            # But MethodView return is (data, code, headers) or just data.
            
            return pagination.items

    @blueprint.route(f'/{url_name}/<int:id>')
    class DetailResource(MethodView):
        @blueprint.doc(security=[{"bearerAuth": []}])
        @blueprint.response(200, schema)
        def get(self, id):
            """Get specific {url_name} by ID (Protected)"""
            return model.query.get_or_404(id)

# --- Register Routes ---
register_read_only_resource(api_bp, User, UserSchema, 'users')
register_read_only_resource(api_bp, Asset, AssetSchema, 'assets')
register_read_only_resource(api_bp, Peripheral, PeripheralSchema, 'peripherals')
register_read_only_resource(api_bp, License, LicenseSchema, 'licenses')
register_read_only_resource(api_bp, Subscription, SubscriptionSchema, 'subscriptions')
register_read_only_resource(api_bp, BusinessService, ServiceSchema, 'services')