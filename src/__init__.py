# src/__init__.py

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import atexit
from flask import Flask, session, render_template, request
from apscheduler.schedulers.background import BackgroundScheduler
import ecs_logging
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_dance.contrib.google import make_google_blueprint
from flask_talisman import Talisman
from flask_smorest import Api

from .extensions import db, migrate
from .models import User
from . import notifications # Added the missing import
import markdown
from markupsafe import Markup
from .seeder_prod import seed_production_frameworks
import re

# --- Rate Limiter (global instance for use in blueprints) ---
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=["200 per day", "50 per hour"]
)

# --- CSRF Protection ---
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()

# --- Content Security Policy ---
talisman = Talisman()

# --- Initialize Extensions ---
def configure_logging(app):
    """
    Configure structured ECS logging with file rotation and console output.
    """
    # Get the app logger
    logger = logging.getLogger(app.name)
    logger.setLevel(logging.INFO)

    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 1. Handler for file output (JSON ECS format)
    # Rotates at 10MB, keeps 5 backup files
    log_file_path = os.path.join(log_dir, 'logs.json')
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(ecs_logging.StdlibFormatter())

    # 2. Handler for console output (JSON ECS format as requested)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ecs_logging.StdlibFormatter())

    # Clear any existing handlers and add the new ones
    logger.handlers = []
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Sync Flask's app.logger with our configured logger
    app.logger.handlers = logger.handlers
    app.logger.setLevel(logger.level)

def create_app(test_config=None):
    """
    Application factory function to create and configure the Flask app.
    
    Args:
        test_config (dict, optional): Configuration dictionary for testing.
                                     If provided, overrides default configuration.
    """
    app = Flask(__name__)

    # --- Configuration ---
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
    
    # Database configuration - supports SQLite or PostgreSQL
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///../data/renewals.db')
    # Handle Heroku-style postgres:// URLs (SQLAlchemy requires postgresql://)
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Log which database backend is being used
    is_postgres = 'postgresql' in database_url
    app.config['IS_POSTGRES'] = is_postgres

    # --- CORRECT UPLOAD FOLDER CONFIG ---
    # Define the project's root directory (where run.py is)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Set the upload folder to data/attachments/ inside the root
    app.config['UPLOAD_FOLDER'] = os.path.join(project_root, 'data', 'attachments')

    # Create the new uploads folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Email configuration
    app.config['SMTP_SERVER'] = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    app.config['SMTP_PORT'] = int(os.environ.get('SMTP_PORT', '587'))
    app.config['EMAIL_USERNAME'] = os.environ.get('EMAIL_USERNAME', '')
    app.config['EMAIL_PASSWORD'] = os.environ.get('EMAIL_PASSWORD', '')
    app.config['WEBHOOK_URL'] = os.environ.get('WEBHOOK_URL', '')

    # --- Google OAuth Configuration ---
    app.config['GOOGLE_OAUTH_CLIENT_ID'] = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '')
    app.config['GOOGLE_OAUTH_CLIENT_SECRET'] = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '')
    # Allow insecure transport for local development
    insecure_transport = os.environ.get('OAUTHLIB_INSECURE_TRANSPORT') == '1'
    if insecure_transport:
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    # --- MFA Configuration ---
    app.config['MFA_ENABLED'] = os.environ.get('MFA_ENABLED', 'False').lower() == 'true'

    # --- Admin User Configuration (for initial setup) ---
    app.config['DEFAULT_ADMIN_EMAIL'] = os.environ.get('DEFAULT_ADMIN_EMAIL', 'admin@example.com')
    app.config['DEFAULT_ADMIN_INITIAL_PASSWORD'] = os.environ.get('DEFAULT_ADMIN_INITIAL_PASSWORD', 'admin123')

    # --- API Configuration ---
    app.config["API_TITLE"] = "OpsDeck API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.2"
    app.config["OPENAPI_URL_PREFIX"] = "/"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = "/swagger-ui"
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    app.config["API_SPEC_OPTIONS"] = {
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            }
        }
    }

    # --- Apply Test Configuration (BEFORE extension initialization) ---
    if test_config is not None:
        app.config.update(test_config)

    # --- Initialize Extensions ---
    db.init_app(app)
    from .extensions import login_manager
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    migrate.init_app(app, db)
    limiter.init_app(app)
    csrf.init_app(app)
    # Disable HTTPS enforcement in development (debug mode) or when explicitly disabled
    is_development = app.debug or insecure_transport or os.environ.get('FLASK_ENV') == 'development'
    talisman.init_app(app, content_security_policy=None, force_https=not is_development)

    # --- Configure Logging (ECS format with rotation) ---
    configure_logging(app)

    # --- Initialize API ---
    api = Api(app)
    from .api import api_bp
    api.register_blueprint(api_bp)

    # --- Custom 429 Error Handler with logging ---
    @app.errorhandler(429)
    def ratelimit_handler(e):
        from .utils.logger import log_audit
        log_audit(
            event_type='security.rate_limit_breach',
            action='block',
            outcome='failure',
            error_message=e.description
        )
        return render_template('429.html', error=e.description), 429
    
    # --- REGISTER THE CUSTOM MARKDOWN FILTER ---
    @app.template_filter('markdown')
    def markdown_filter(s):
        return markdown.markdown(s)
    
    @app.template_filter('nl2br')
    def nl2br_filter(s):
        """Converts newlines in a string to HTML <br> tags."""
        return Markup(re.sub(r'\n', '<br>\n', s))

    # --- Register Blueprints ---
    from .routes.main import main_bp
    from .routes.assets import assets_bp
    from .routes.peripherals import peripherals_bp
    from .routes.locations import locations_bp
    from .routes.suppliers import suppliers_bp
    from .routes.contacts import contacts_bp
    from .routes.users import users_bp
    from .routes.groups import groups_bp
    from .routes.payment_methods import payment_methods_bp
    from .routes.tags import tags_bp
    from .routes.subscriptions import subscriptions_bp
    from .routes.licenses import licenses_bp
    from .routes.software import software_bp
    from .routes.purchases import purchases_bp
    from .routes.budgets import budgets_bp
    from .routes.reports import reports_bp
    from .routes.attachments import attachments_bp
    from .routes.treeview import treeview_bp
    from .routes.admin import admin_bp
    from .routes.opportunities import opportunities_bp
    from .routes.policies import policies_bp
    from .routes.compliance import compliance_bp
    from .routes.risk import risk_bp
    from .routes.training import training_bp
    from .routes.maintenance import maintenance_bp
    from .routes.disposal import disposal_bp
    from .routes.leads import leads_bp
    from .routes.documentation import documentation_bp
    from .routes.frameworks import frameworks_bp
    from .routes.links import links_bp
    from .routes.activities import activities_bp
    from .routes.onboarding import onboarding_bp
    from .routes.credentials import credentials_bp

    # --- Favicon Route ---
    from flask import send_from_directory
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                   'favicon.ico', mimetype='image/vnd.microsoft.icon')

    app.register_blueprint(main_bp)
    app.register_blueprint(assets_bp, url_prefix='/assets')
    app.register_blueprint(peripherals_bp, url_prefix='/peripherals')
    app.register_blueprint(locations_bp, url_prefix='/locations')
    app.register_blueprint(suppliers_bp, url_prefix='/suppliers')
    app.register_blueprint(contacts_bp, url_prefix='/contacts')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(groups_bp, url_prefix='/groups')
    app.register_blueprint(payment_methods_bp, url_prefix='/payment-methods')
    app.register_blueprint(tags_bp, url_prefix='/tags')
    app.register_blueprint(subscriptions_bp, url_prefix='/subscriptions')
    app.register_blueprint(licenses_bp)
    app.register_blueprint(software_bp)
    app.register_blueprint(purchases_bp, url_prefix='/purchases')
    app.register_blueprint(budgets_bp, url_prefix='/budgets')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(attachments_bp, url_prefix='/attachments')
    app.register_blueprint(treeview_bp, url_prefix='/tree-view')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(opportunities_bp, url_prefix='/opportunities')
    app.register_blueprint(policies_bp, url_prefix='/policies')
    app.register_blueprint(compliance_bp, url_prefix='/compliance')
    app.register_blueprint(risk_bp, url_prefix='/risk')
    app.register_blueprint(training_bp, url_prefix='/training')
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(disposal_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(documentation_bp, url_prefix='/documentation')
    app.register_blueprint(frameworks_bp)
    from .routes.audits import audits_bp
    app.register_blueprint(audits_bp)
    from .routes.services import services_bp
    app.register_blueprint(services_bp)
    from .routes.cost_centers import cost_centers_bp
    app.register_blueprint(cost_centers_bp, url_prefix='/cost-centers')
    app.register_blueprint(links_bp, url_prefix='/links')
    app.register_blueprint(activities_bp, url_prefix='/security/activities')
    app.register_blueprint(onboarding_bp, url_prefix='/onboarding')
    from .routes.risk_assessment import risk_assessment_bp
    app.register_blueprint(risk_assessment_bp)
    from .routes.credentials import credentials_bp
    from .routes.certificates import certificates_bp
    app.register_blueprint(credentials_bp)
    app.register_blueprint(certificates_bp)
    
    from .routes.configuration import configuration_bp
    app.register_blueprint(configuration_bp, url_prefix='/configuration')
    
    from .routes.admin_communications import admin_communications_bp
    app.register_blueprint(admin_communications_bp, url_prefix='/admin/communications')
    
    from .routes.admin_notifications import admin_notifications_bp
    app.register_blueprint(admin_notifications_bp, url_prefix='/admin/notifications')
    
    from .routes.campaigns import campaigns_bp
    app.register_blueprint(campaigns_bp, url_prefix='/campaigns')
    
    from .routes.organization import organization_bp
    app.register_blueprint(organization_bp, url_prefix='/settings/organization')


    # --- Google OAuth Blueprint ---
    if app.config.get('GOOGLE_OAUTH_CLIENT_ID'):
        google_bp = make_google_blueprint(
            client_id=app.config['GOOGLE_OAUTH_CLIENT_ID'],
            client_secret=app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
            scope=["profile", "email"],
            redirect_to="main.google_callback"
        )
        app.register_blueprint(google_bp, url_prefix="/login")


    # --- Make user and role available in all templates ---
    @app.context_processor
    def inject_user_context():
        user_id = session.get('user_id')
        if user_id:
            user = User.query.get(user_id)
            if user:
                return dict(current_user=user, current_user_role=user.role)
        return dict(current_user=None, current_user_role=None)

    # --- Force admin to change the default password ---
    from .routes.main import password_change_required
    @app.before_request
    def before_request_hook():
        # This now correctly calls the updated password_change_required decorator
        password_change_required(lambda: None)()

    # --- Scheduler and Notifications ---
    # Only start the scheduler if not in testing mode
    if not app.config.get('TESTING'):
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=notifications.check_upcoming_renewals,
            args=[app],
            trigger="interval",
            days=1
        )
        scheduler.add_job(
            func=notifications.check_credential_expirations,
            args=[app],
            trigger="interval",
            days=1
        )
        scheduler.add_job(
            func=notifications.check_certificate_expirations,
            args=[app],
            trigger="interval",
            days=1
        )
        # Communications engine - process scheduled emails every 5 minutes for faster delivery
        scheduler.add_job(
            func=notifications.process_communications_queue,
            args=[app],
            trigger="interval",
            minutes=5
        )
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown())

    # --- CLI Commands ---
    @app.cli.command("init-db")
    def init_db_command():
        """Creates the database tables and a default admin user if none exists."""
        with app.app_context():
            db.create_all()
            
            # Get admin credentials from configuration (environment variables)
            email = app.config.get('DEFAULT_ADMIN_EMAIL')
            password = app.config.get('DEFAULT_ADMIN_INITIAL_PASSWORD')
            
            if not email or not password:
                print("Error: Admin credentials not configured.")
                return
            
            # Check if admin user already exists (idempotency)
            existing_admin = User.query.filter_by(email=email).first()
            if existing_admin:
                print(f"Admin user '{email}' already exists. Skipping creation.")
                return
            
            # Create the admin user (hidden from org chart as it's a break-glass account)
            admin_user = User(name='Administrator', email=email, role='admin', hide_from_org_chart=True)
            admin_user.set_password(password)
            db.session.add(admin_user)
            db.session.commit()
            print(f"✓ Admin user created successfully: {email}")
    
    # --- Seed the db with fake demo data ---
    @app.cli.command("seed-db-demodata")
    def seed_db_command():
        """Seeds the database with demo data."""
        from .seeder import seed_data
        seed_data()

    @app.cli.command('seed-db-prod')
    def seed_prod_command():
        """Carga los datos maestros de producción (Frameworks & Threats)."""
        seed_production_frameworks()
        from .seeder_prod import seed_threats
        seed_threats()

    # --- Importar CLI Commands (Data Import) ---
    from . import cli
    cli.register_commands(app)

    return app