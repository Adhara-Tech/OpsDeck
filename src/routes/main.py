from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
)
import os
from sqlalchemy import or_
from markupsafe import Markup
from functools import wraps
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
from ..models import db, User, UserKnownIP, Subscription, NotificationSetting, Asset, Supplier, Contact, Purchase, Peripheral, Location, PaymentMethod, License, MaintenanceLog
from ..models.security import SecurityIncident, Risk, Framework, FrameworkControl
from ..models.credentials import Credential, CredentialSecret
from ..models.certificates import Certificate, CertificateVersion
from ..models.audits import ComplianceAudit
from src import limiter
from src import notifications
import calendar
import random

main_bp = Blueprint('main', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

def is_break_glass_admin(user):
    """Check if the user is the break-glass admin account."""
    if not user:
        return False
    default_admin_email = current_app.config.get('DEFAULT_ADMIN_EMAIL', 'admin@example.com')
    return user.email == default_admin_email

from src.utils.logger import log_audit

@main_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            # Credentials valid - check if MFA is needed
            return verify_ip_and_login(user)
        else:
            # Log failed login attempt
            log_audit(
                event_type='security.login',
                action='login',
                outcome='failure',
                target_object=email,
                error_message='Invalid email or password'
            )
            flash('Invalid email or password')

    return render_template('login.html')


@main_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for Kubernetes probes.
    Returns 200 OK if the application is running.
    No rate limiting or authentication required.
    """
    return jsonify({'status': 'healthy'}), 200



def verify_ip_and_login(user):
    """Verify user's IP and either login directly or trigger MFA flow."""
    ip = request.remote_addr
    
    # Check if IP is known for this user
    known_ip = UserKnownIP.query.filter_by(
        user_id=user.id,
        ip_address=ip
    ).first()
    
    # If IP is known or MFA is disabled -> direct login
    if known_ip or not current_app.config.get('MFA_ENABLED', False):
        if known_ip:
            known_ip.last_seen = datetime.utcnow()
            db.session.commit()
        
        # Log successful login
        log_audit(
            event_type='security.login',
            action='login',
            outcome='success',
            target_object=f"User:{user.id}",
            user_email=user.email # Explicitly passed as session isn't set yet
        )
        session['user_id'] = user.id
        flash('Logged in successfully', 'success')
        return redirect(url_for('main.organizational_health'))
    
    # --- NEW IP DETECTED: Trigger MFA ---
    
    # Generate 6-digit OTP
    otp = "".join([str(random.randint(0, 9)) for _ in range(6)])
    
    # Store MFA session data (expires in 10 min)
    session['mfa_user_id'] = user.id
    session['mfa_otp'] = otp
    session['mfa_expiry'] = (datetime.utcnow() + timedelta(minutes=10)).timestamp()
    
    # Send OTP email
    email_body = f"""
    <h2>Código de Verificación de Seguridad</h2>
    <p>Se ha detectado un intento de inicio de sesión desde una nueva ubicación.</p>
    <p>Tu código de verificación es:</p>
    <h1 style="font-size: 32px; letter-spacing: 5px; font-family: monospace;">{otp}</h1>
    <p>Este código expira en 10 minutos.</p>
    <p>Si no has intentado iniciar sesión, ignora este correo.</p>
    """
    notifications.send_email(
        current_app._get_current_object(),
        "OpsDeck - Código de Verificación",
        email_body,
        [user.email]
    )
    
    # Log MFA code sent (without revealing the code)
    log_audit(
        event_type='security.mfa',
        action='send_code',
        outcome='success',
        target_object=f"User:{user.id}",
        user_email=user.email
    )
    
    flash('Nuevo dispositivo detectado. Revisa tu email para el código de verificación.', 'info')
    return redirect(url_for('main.mfa_verify'))


@main_bp.route('/mfa-verify', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def mfa_verify():
    """Handle MFA verification."""
    # Check if MFA session exists
    if 'mfa_user_id' not in session:
        return redirect(url_for('main.login'))
    
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        stored_otp = session.get('mfa_otp')
        expiry = session.get('mfa_expiry')
        user_id = session.get('mfa_user_id')
        
        # Check if session is expired
        if not stored_otp or datetime.utcnow().timestamp() > expiry:
            # Clear MFA session
            session.pop('mfa_user_id', None)
            session.pop('mfa_otp', None)
            session.pop('mfa_expiry', None)
            flash('El código ha expirado. Por favor, inicia sesión de nuevo.', 'warning')
            return redirect(url_for('main.login'))
        
        if code == stored_otp:
            # SUCCESS - Get user and complete login
            user = User.query.get(user_id)
            if user:
                # Save the new IP to whitelist
                new_ip = UserKnownIP(
                    user_id=user.id,
                    ip_address=request.remote_addr
                )
                db.session.add(new_ip)
                db.session.commit()
                
                # Clear MFA session
                session.pop('mfa_user_id', None)
                session.pop('mfa_otp', None)
                session.pop('mfa_expiry', None)
                
                # Log successful MFA verification
                log_audit(
                    event_type='security.mfa',
                    action='verify',
                    outcome='success',
                    target_object=f"User:{user.id}",
                    user_email=user.email
                )
                
                # Complete login
                session['user_id'] = user.id
                flash('Dispositivo verificado. Bienvenido.', 'success')
                return redirect(url_for('main.organizational_health'))
        
        # FAILURE - Wrong code
        log_audit(
            event_type='security.mfa',
            action='verify',
            outcome='failure',
            target_object=f"User:{user_id}",
            error_message="Invalid MFA code"
        )
        flash('Código incorrecto. Inténtalo de nuevo.', 'danger')
    
    return render_template('mfa.html')

@main_bp.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('main.login'))


@main_bp.route('/impersonate/<int:user_id>', methods=['POST'])
@login_required
def impersonate(user_id):
    """Start impersonating another user (break-glass admin only)."""
    # Get current user
    current_user = User.query.get(session['user_id'])
    
    # Verify current user is the break-glass admin
    if not is_break_glass_admin(current_user):
        log_audit(
            event_type='security.impersonation',
            action='attempt',
            outcome='failure',
            target_object=f"User:{user_id}",
            error_message='Unauthorized impersonation attempt - not break-glass admin'
        )
        flash('Unauthorized: Only the break-glass admin can impersonate users.', 'danger')
        return redirect(url_for('users.users'))
    
    # Get target user
    target_user = User.query.get_or_404(user_id)
    
    # Prevent impersonating yourself
    if current_user.id == target_user.id:
        flash('You cannot impersonate yourself.', 'warning')
        return redirect(url_for('users.users'))
    
    # Store original user ID and start impersonation
    session['original_user_id'] = current_user.id
    session['user_id'] = target_user.id
    
    # Log the impersonation start
    log_audit(
        event_type='security.impersonation',
        action='start',
        outcome='success',
        target_object=f"User:{target_user.id}",
        user_email=current_user.email,
        details=f"Admin {current_user.email} started impersonating {target_user.email}"
    )
    
    flash(f'Now impersonating: {target_user.name} ({target_user.email})', 'info')
    return redirect(url_for('main.organizational_health'))


@main_bp.route('/stop-impersonate', methods=['POST'])
@login_required
def stop_impersonate():
    """Stop impersonating and return to original user."""
    # Check if currently impersonating
    original_user_id = session.get('original_user_id')
    if not original_user_id:
        flash('You are not currently impersonating anyone.', 'warning')
        return redirect(url_for('main.organizational_health'))
    
    # Get both users for logging
    impersonated_user = User.query.get(session['user_id'])
    original_user = User.query.get(original_user_id)
    
    # Restore original user session
    session['user_id'] = original_user_id
    session.pop('original_user_id', None)
    
    # Log the impersonation end
    log_audit(
        event_type='security.impersonation',
        action='stop',
        outcome='success',
        target_object=f"User:{impersonated_user.id if impersonated_user else 'Unknown'}",
        user_email=original_user.email if original_user else 'Unknown',
        details=f"Admin {original_user.email if original_user else 'Unknown'} stopped impersonating"
    )
    
    flash('Impersonation ended. Returned to your account.', 'success')
    return redirect(url_for('users.users'))


@main_bp.route('/google/callback')
def google_callback():
    """Handle Google OAuth callback and authenticate user."""
    from flask_dance.contrib.google import google
    
    if not google.authorized:
        log_audit(
            event_type='security.login_oauth',
            action='login',
            outcome='failure',
            error_message="Google not authorized"
        )
        flash('Error al autorizar con Google', 'danger')
        return redirect(url_for('main.login'))
    
    # Get user info from Google
    try:
        resp = google.get("/oauth2/v2/userinfo")
        if not resp.ok:
            log_audit(
                event_type='security.login_oauth',
                action='login',
                outcome='failure',
                error_message=f"Google API error: {resp.status_code}"
            )
            flash('Error al obtener información de Google', 'danger')
            return redirect(url_for('main.login'))
        
        google_info = resp.json()
        email = google_info.get("email")
    except Exception as e:
        current_app.logger.error(f"Exception during Google OAuth: {str(e)}")
        log_audit(
            event_type='security.login_oauth',
            action='login',
            outcome='failure',
            error_message=str(e)
        )
        flash('Error al procesar la autenticación de Google', 'danger')
        return redirect(url_for('main.login'))
    
    # Find user in database
    user = User.query.filter_by(email=email).first()
    
    if user:
        # Success - log and create session
        log_audit(
            event_type='security.login_oauth',
            action='login',
            outcome='success',
            target_object=f"User:{user.id}",
            user_email=email,
            provider="google"
        )
        session['user_id'] = user.id
        flash('Logged in successfully via Google', 'success')
        return redirect(url_for('main.organizational_health'))
    else:
        # User not found in database
        log_audit(
            event_type='security.login_oauth',
            action='login',
            outcome='failure',
            target_object=email,
            error_message="User not found in database"
        )
        flash('No existe un usuario registrado con este email.', 'danger')
        return redirect(url_for('main.login'))

def password_change_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if user_id:
            user = User.query.get(user_id)
            # Get configured admin credentials from app config
            default_admin_email = current_app.config.get('DEFAULT_ADMIN_EMAIL', 'admin@example.com')
            default_admin_password = current_app.config.get('DEFAULT_ADMIN_INITIAL_PASSWORD', 'admin123')
            
            # Check if user is using the default admin credentials
            if user and user.email == default_admin_email and user.check_password(default_admin_password):
                if request.endpoint not in ['main.change_password', 'main.logout', 'static']:
                    # Redirect without flash message - the UI will show the forced change alert
                    return redirect(url_for('main.change_password'))
        return f(*args, **kwargs)
    return decorated_function

@main_bp.route('/')
@login_required
def organizational_health():
    """Executive Organizational Health Dashboard - Landing Page."""
    today = date.today()
    ninety_days = today + timedelta(days=90)
    
    # ----- HEALTH SCORE CALCULATION -----
    # Based on inverse of critical/high risks (Excluding Closed and Accepted)
    critical_risks = Risk.query.filter(
        Risk.status != 'Closed',
        Risk.treatment_strategy != 'Accept',
        Risk.residual_likelihood >= 4, 
        Risk.residual_impact >= 4
    ).count()
    
    high_risks = Risk.query.filter(
        Risk.status != 'Closed',
        Risk.treatment_strategy != 'Accept',
        Risk.residual_likelihood >= 3, 
        Risk.residual_impact >= 3
    ).count()
    health_score = max(0, 100 - (critical_risks * 15) - (high_risks * 5))
    
    # ----- GLOBAL STATUS -----
    active_incidents = SecurityIncident.query.filter(
        SecurityIncident.status.in_(['Open', 'Investigating', 'Escalated'])
    ).count()
    
    if critical_risks > 0 or active_incidents > 0:
        global_status = 'critical'
    elif high_risks > 2:
        global_status = 'degraded'
    else:
        global_status = 'operational'
    
    # ----- CRITICAL ACTION ITEMS (RED STATE) -----
    critical_items = []
    
    # Active high-severity incidents
    incidents = SecurityIncident.query.filter(
        SecurityIncident.status.in_(['Open', 'Investigating', 'Escalated']),
        SecurityIncident.severity.in_(['SEV-1', 'SEV-2', 'P1', 'P2'])
    ).limit(5).all()
    for inc in incidents:
        critical_items.append({
            'type': 'security',
            'severity': 'critical',
            'title': inc.title,
            'description': f'{inc.severity} - {inc.status}',
            'link': url_for('compliance.incident_detail', id=inc.id)
        })
    
    # Overdue maintenance
    overdue_logs = MaintenanceLog.query.filter(
        MaintenanceLog.status == 'Pending',
        MaintenanceLog.event_date < today
    ).limit(5).all()
    for log in overdue_logs:
        critical_items.append({
            'type': 'operational',
            'severity': 'high',
            'title': f'{log.asset.name if log.asset else "Unknown"} - Maintenance Overdue',
            'description': log.description[:50] if log.description else 'Scheduled maintenance delayed',
            'link': url_for('maintenance.log_detail', id=log.id)
        })
    
    # Expired credentials
    expired_secrets = CredentialSecret.query.filter(
        CredentialSecret.is_active == True,
        CredentialSecret.expires_at < datetime.utcnow()
    ).limit(5).all()
    for secret in expired_secrets:
        critical_items.append({
            'type': 'security',
            'severity': 'critical',
            'title': f'{secret.credential.name} - Credential Expired',
            'description': f'Type: {secret.credential.type}',
            'link': url_for('credentials.credential_detail', id=secret.credential.id)
        })
    
    # Expired certificates (still active)
    expired_certs = CertificateVersion.query.filter(
        CertificateVersion.is_active == True,
        CertificateVersion.expires_at < today
    ).limit(5).all()
    for cv in expired_certs:
        critical_items.append({
            'type': 'security',
            'severity': 'critical',
            'title': f'{cv.certificate.name} - Certificate Expired',
            'description': f'Expired: {cv.expires_at.strftime("%Y-%m-%d")}' if cv.expires_at else 'Expired',
            'link': url_for('certificates.certificate_detail', id=cv.certificate.id)
        })
    
    # ----- EXPIRATION HORIZON (YELLOW STATE) -----
    expirations = {'finance': [], 'identity': [], 'certificates': [], 'legal': []}
    
    # Financial: Payment Methods
    payment_methods = PaymentMethod.query.filter(
        PaymentMethod.is_archived == False,
        PaymentMethod.expiry_date.isnot(None)
    ).all()
    for pm in payment_methods:
        last_day = pm.expiry_date.replace(day=calendar.monthrange(pm.expiry_date.year, pm.expiry_date.month)[1])
        if today <= last_day <= ninety_days:
            days = (last_day - today).days
            expirations['finance'].append({
                'name': pm.name,
                'days': days,
                'meta': pm.details or pm.method_type
            })
    expirations['finance'].sort(key=lambda x: x['days'])
    
    # Identity: Credentials
    expiring_secrets = CredentialSecret.query.filter(
        CredentialSecret.is_active == True,
        CredentialSecret.expires_at.isnot(None),
        CredentialSecret.expires_at > datetime.utcnow(),
        CredentialSecret.expires_at <= datetime.utcnow() + timedelta(days=90)
    ).all()
    for secret in expiring_secrets:
        days = (secret.expires_at.date() - today).days
        expirations['identity'].append({
            'name': secret.credential.name,
            'type': secret.credential.type,
            'days': days
        })
    expirations['identity'].sort(key=lambda x: x['days'])
    
    # Certificates
    cert_versions = CertificateVersion.query.filter(
        CertificateVersion.is_active == True,
        CertificateVersion.expires_at > today,
        CertificateVersion.expires_at <= ninety_days
    ).all()
    for cv in cert_versions:
        days = (cv.expires_at - today).days
        expirations['certificates'].append({
            'name': cv.certificate.name,
            'issuer': cv.issuer,
            'days': days
        })
    expirations['certificates'].sort(key=lambda x: x['days'])
    
    # Legal: Subscriptions & Licenses
    subscriptions = Subscription.query.filter_by(is_archived=False).all()
    for sub in subscriptions:
        next_renewal = sub.next_renewal_date
        if today <= next_renewal <= ninety_days:
            days = (next_renewal - today).days
            expirations['legal'].append({
                'name': sub.name,
                'cost': sub.cost_eur,
                'days': days
            })
    
    licenses = License.query.filter(
        License.expiry_date > today,
        License.expiry_date <= ninety_days
    ).all()
    for lic in licenses:
        days = (lic.expiry_date - today).days
        expirations['legal'].append({
            'name': lic.name,
            'cost': None,
            'days': days
        })
    expirations['legal'].sort(key=lambda x: x['days'])
    
    # ----- COUNTS -----
    critical_count = len(critical_items)
    warning_count = sum(len(v) for v in expirations.values() if v and all(item['days'] <= 30 for item in v[:1]))
    expiring_count = sum(len(v) for v in expirations.values())
    
    # ----- OPS SUMMARY -----
    total_assets = Asset.query.filter(
        Asset.is_archived == False,
        Asset.status != 'Decommissioned'
    ).count()
    healthy_assets = Asset.query.filter_by(is_archived=False, status='In Use').count()
    asset_health = int((healthy_assets / total_assets * 100) if total_assets > 0 else 100)
    
    # Monthly spend projection from subscriptions
    this_month_start = today.replace(day=1)
    next_month_start = this_month_start + relativedelta(months=1)
    projected_spend = sum(
        sub.cost_eur for sub in subscriptions
        if sub.next_renewal_date and this_month_start <= sub.next_renewal_date < next_month_start
    )
    
    ops_summary = {
        'projected_spend': projected_spend,
        'spend_trend': 0,  # TODO: Calculate from historical data
        'asset_health': asset_health,
        'healthy_assets': healthy_assets,
        'total_assets': total_assets
    }
    
    # ----- COMPLIANCE SUMMARY -----
    total_controls = FrameworkControl.query.join(Framework).filter(Framework.is_active == True).count()
    # Controls with at least one compliance link are considered "compliant"
    from sqlalchemy import func
    from ..models.security import ComplianceLink
    compliant_controls = db.session.query(func.count(func.distinct(ComplianceLink.framework_control_id))).scalar() or 0
    compliance_score = int((compliant_controls / total_controls * 100) if total_controls > 0 else 100)
    pending_audits = ComplianceAudit.query.filter(ComplianceAudit.status.in_(['Prep', 'In Progress'])).count()
    
    compliance_summary = {
        'score': compliance_score,
        'compliant_controls': compliant_controls,
        'total_controls': total_controls,
        'pending_audits': pending_audits
    }
    
    return render_template(
        'organizational_health.html',
        today=today,
        health_score=health_score,
        global_status=global_status,
        critical_items=critical_items,
        critical_count=critical_count,
        warning_count=warning_count,
        expiring_count=expiring_count,
        expirations=expirations,
        ops_summary=ops_summary,
        compliance_summary=compliance_summary
    )


@main_bp.route('/operations')
@login_required
def ops_finance_dashboard():
    # --- STAT CARD COUNTS ---
    stats = {
        'subscriptions': Subscription.query.filter_by(is_archived=False).count(),
        'assets': Asset.query.filter_by(is_archived=False).count(),
        'peripherals': Peripheral.query.filter_by(is_archived=False).count(),
        'suppliers': Supplier.query.filter_by(is_archived=False).count(),
        'users': User.query.filter_by(is_archived=False).count(),
        'locations': Location.query.filter_by(is_archived=False).count(),
        'contacts': Contact.query.filter_by(is_archived=False).count(),
        'payment_methods': PaymentMethod.query.filter_by(is_archived=False).count(),
    }

    # --- Upcoming Renewals & Filter Logic ---
    period = request.args.get('period', '30', type=str)
    today = date.today()

    if period == '7':
        start_date, end_date = today, today + timedelta(days=7)
    elif period == '90':
        start_date, end_date = today, today + timedelta(days=90)
    elif period == 'current_month':
        start_date = today.replace(day=1)
        end_date = start_date + relativedelta(months=+1, days=-1)
    elif period == 'next_month':
        start_date = (today.replace(day=1) + relativedelta(months=+1))
        end_date = start_date + relativedelta(months=+1, days=-1)
    else:
        period = '30'
        start_date, end_date = today, today + timedelta(days=30)

    all_active_subscriptions = Subscription.query.filter_by(is_archived=False).all()
    upcoming_renewals, total_cost = [], 0

    for subscription in all_active_subscriptions:
        next_renewal = subscription.next_renewal_date
        while next_renewal <= end_date:
            if next_renewal >= start_date:
                upcoming_renewals.append((next_renewal, subscription))
                total_cost += subscription.cost_eur
            next_renewal = subscription.get_renewal_date_after(next_renewal)
            
    upcoming_renewals.sort(key=lambda x: x[0])

    # --- Forecast Chart Logic ---
    forecast_start_date = today.replace(day=1)
    end_of_forecast_period = forecast_start_date + relativedelta(months=+13)

    forecast_labels, forecast_keys, forecast_costs = [], [], {}
    for i in range(13):
        month_date = forecast_start_date + relativedelta(months=+i)
        year_month_key = month_date.strftime('%Y-%m')
        forecast_labels.append(month_date.strftime('%b %Y'))
        forecast_keys.append(year_month_key)
        forecast_costs[year_month_key] = 0

    for subscription in all_active_subscriptions:
        renewal = subscription.renewal_date
        # Find first renewal within or after forecast start
        while renewal < forecast_start_date:
            renewal = subscription.get_renewal_date_after(renewal)
        
        while renewal < end_of_forecast_period:
            year_month_key = renewal.strftime('%Y-%m')
            if year_month_key in forecast_costs:
                forecast_costs[year_month_key] += subscription.cost_eur
            renewal = subscription.get_renewal_date_after(renewal)

    forecast_data = [round(cost, 2) for cost in forecast_costs.values()]

    # --- CORRECTED: EXPIRING ITEMS LOGIC ---
    thirty_days_from_now = today + timedelta(days=30)
    
    # Query only non-archived items with warranty info
    expiring_assets = Asset.query.filter(
        Asset.is_archived == False,
        Asset.purchase_date.isnot(None), 
        Asset.warranty_length.isnot(None)
    ).all()
    expiring_peripherals = Peripheral.query.filter(
        Peripheral.is_archived == False,
        Peripheral.purchase_date.isnot(None), 
        Peripheral.warranty_length.isnot(None)
    ).all()
    
    all_expiring_items = [
        item for item in expiring_assets + expiring_peripherals 
        if item.warranty_end_date and today <= item.warranty_end_date <= thirty_days_from_now
    ]
    all_expiring_items.sort(key=lambda x: x.warranty_end_date)

    # CORRECTED: Payment methods expiring in the next 90 days
    ninety_days_from_now = today + timedelta(days=90)
    expiring_payment_methods = []
    all_payment_methods = PaymentMethod.query.filter(
        PaymentMethod.is_archived == False,
        PaymentMethod.expiry_date.isnot(None)
    ).order_by(PaymentMethod.expiry_date).all()

    for method in all_payment_methods:
        # Find the last day of the expiry month
        last_day_of_expiry_month = method.expiry_date.replace(day=calendar.monthrange(method.expiry_date.year, method.expiry_date.month)[1])
        if today <= last_day_of_expiry_month <= ninety_days_from_now:
            expiring_payment_methods.append(method)

    return render_template(
        'ops_finance_dashboard.html',
        stats=stats,
        upcoming_renewals=upcoming_renewals,
        total_cost=total_cost,
        selected_period=period,
        today=today,
        forecast_labels=forecast_labels,
        forecast_keys=forecast_keys,
        forecast_data=forecast_data,
        expiring_items=all_expiring_items,
        expiring_payment_methods=expiring_payment_methods
    )


@main_bp.route('/notifications', methods=['GET', 'POST'])
@login_required
def notification_settings():
    settings = NotificationSetting.query.first()
    if not settings:
        settings = NotificationSetting()
        db.session.add(settings)
        db.session.commit()

    if request.method == 'POST':
        settings.email_enabled = 'email_enabled' in request.form
        settings.email_recipient = request.form.get('email_recipient')
        settings.webhook_enabled = 'webhook_enabled' in request.form
        settings.webhook_url = request.form.get('webhook_url')

        days_before = request.form.getlist('days_before')
        settings.notify_days_before = ','.join(days_before)

        db.session.commit()
        flash('Notification settings updated successfully!')
        return redirect(url_for('main.notification_settings'))

    notify_days_list = [int(day) for day in settings.notify_days_before.split(',') if day]

    return render_template(
        'notifications/settings.html',
        settings=settings,
        notify_days_list=notify_days_list
    )

@main_bp.route('/api/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    results = []

    if len(query) < 2:
        return jsonify([])

    search_term = f'%{query}%'
    limit = 5

    # Search Subscriptions
    subscriptions = Subscription.query.filter(Subscription.name.ilike(search_term), not Subscription.is_archived).limit(limit).all()
    for item in subscriptions:
        results.append({
            'name': item.name,
            'type': 'Subscription',
            'url': url_for('subscriptions.subscription_detail', id=item.id)
        })

    # Search Assets
    assets = Asset.query.filter(
        or_(
            Asset.name.ilike(search_term),
            Asset.serial_number.ilike(search_term)
        ), not Asset.is_archived
    ).limit(limit).all()
    for item in assets:
        results.append({
            'name': item.name,
            'type': 'Asset',
            'url': url_for('assets.asset_detail', id=item.id)
        })

    # Search Suppliers
    suppliers = Supplier.query.filter(Supplier.name.ilike(search_term), not Supplier.is_archived).limit(limit).all()
    for item in suppliers:
        results.append({
            'name': item.name,
            'type': 'Supplier',
            'url': url_for('suppliers.supplier_detail', id=item.id)
        })

    # Search Contacts
    contacts = Contact.query.filter(Contact.name.ilike(search_term), not Contact.is_archived).limit(limit).all()
    for item in contacts:
        results.append({
            'name': f"{item.name} ({item.supplier.name})",
            'type': 'Contact',
            'url': url_for('contacts.contact_detail', id=item.id)
        })
    
    # Search Purchases
    purchases = Purchase.query.filter(Purchase.description.ilike(search_term)).limit(limit).all()
    for item in purchases:
        results.append({
            'name': item.description,
            'type': 'Purchase',
            'url': url_for('purchases.purchase_detail', id=item.id)
        })

    # Search Peripherals
    peripherals = Peripheral.query.filter(
        or_(
            Peripheral.name.ilike(search_term),
            Peripheral.serial_number.ilike(search_term)
        ), not Peripheral.is_archived
    ).limit(limit).all()
    for item in peripherals:
        results.append({
            'name': item.name,
            'type': 'Peripheral',
            'url': url_for('peripherals.edit_peripheral', id=item.id)
        })

    return jsonify(results)


@main_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    user = User.query.get(session['user_id'])
    
    # Detect if this is a forced password change
    default_admin_email = current_app.config.get('DEFAULT_ADMIN_EMAIL', 'admin@example.com')
    default_admin_password = current_app.config.get('DEFAULT_ADMIN_INITIAL_PASSWORD', 'admin123')
    forced_change = False
    
    if user and user.email == default_admin_email and user.check_password(default_admin_password):
        forced_change = True
    
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not user.check_password(current_password):
            flash('Your current password was incorrect.', 'danger')
        elif new_password != confirm_password:
            flash('The new passwords do not match.', 'danger')
        elif len(new_password) < 8:
            flash('The new password must be at least 8 characters long.', 'danger')
        else:
            user.set_password(new_password)
            db.session.commit()
            
            log_audit(
                event_type='security.password_change',
                action='update',
                target_object=f"User:{user.id}"
            )
            
            flash('Your password has been updated successfully!', 'success')
            return redirect(url_for('main.organizational_health'))

    return render_template('change_password.html', forced_change=forced_change)


@main_bp.route('/my-api-key')
@login_required
def my_api_key():
    """Render the API Key management page for the current user."""
    return render_template('api_key.html')


@main_bp.route('/my-api-key/generate', methods=['POST'])
@login_required
def generate_my_token():
    """Generate a new API token for the current user."""
    user = User.query.get(session['user_id'])
    user.generate_token()
    db.session.commit()
    
    log_audit(
        event_type='security.token_generated',
        action='create',
        target_object=f"User:{user.id}",
        user_email=user.email,
        description="User generated their own API token"
    )
    
    flash('New API Token generated successfully.', 'success')
    return redirect(url_for('main.my_api_key'))


# --- INTERNAL ROUTES (No Login Required) ---
# These routes are designed to be called by Flask CLI commands

@main_bp.route('/internal/test-db')
def internal_test_db():
    """
    Internal route for database connectivity testing.
    Performs a simple query to verify database connection.
    """
    try:
        # Query the User table to verify database connectivity
        user_count = User.query.count()
        
        # Get database information
        db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured')
        # Mask sensitive information in the URI
        if '@' in db_uri:
            # For postgres://user:pass@host/db format
            parts = db_uri.split('@')
            masked_uri = parts[0].split(':')[0] + ':***@' + '@'.join(parts[1:])
        else:
            masked_uri = db_uri
        
        is_postgres = current_app.config.get('IS_POSTGRES', False)
        db_type = 'PostgreSQL' if is_postgres else 'SQLite'
        
        return jsonify({
            'status': 'success',
            'message': 'Database connection successful',
            'database_type': db_type,
            'database_uri': masked_uri,
            'user_count': user_count,
            'query_executed': 'SELECT COUNT(*) FROM user'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Database connection failed',
            'error': str(e)
        }), 500


@main_bp.route('/internal/app-info')
def internal_app_info():
    """
    Internal route for retrieving application configuration information.
    Returns non-sensitive configuration details.
    """
    try:
        # Get database information
        db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured')
        if '@' in db_uri:
            parts = db_uri.split('@')
            masked_uri = parts[0].split(':')[0] + ':***@' + '@'.join(parts[1:])
        else:
            masked_uri = db_uri
        
        is_postgres = current_app.config.get('IS_POSTGRES', False)
        db_type = 'PostgreSQL' if is_postgres else 'SQLite'
        
        # Gather application configuration
        app_info = {
            'status': 'success',
            'app_name': current_app.config.get('API_TITLE', 'OpsDeck'),
            'api_version': current_app.config.get('API_VERSION', 'v1'),
            'database': {
                'type': db_type,
                'uri': masked_uri,
                'track_modifications': current_app.config.get('SQLALCHEMY_TRACK_MODIFICATIONS', False)
            },
            'security': {
                'mfa_enabled': current_app.config.get('MFA_ENABLED', False),
                'secret_key_configured': bool(current_app.config.get('SECRET_KEY')),
                'testing_mode': current_app.config.get('TESTING', False)
            },
            'email': {
                'smtp_server': current_app.config.get('SMTP_SERVER', 'Not configured'),
                'smtp_port': current_app.config.get('SMTP_PORT', 'Not configured'),
                'email_configured': bool(current_app.config.get('EMAIL_USERNAME'))
            },
            'oauth': {
                'google_oauth_configured': bool(current_app.config.get('GOOGLE_OAUTH_CLIENT_ID'))
            },
            'paths': {
                'upload_folder': current_app.config.get('UPLOAD_FOLDER', 'Not configured')
            }
        }
        
        return jsonify(app_info), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve app info',
            'error': str(e)
        }), 500

@main_bp.route('/internal/test-email')
def internal_test_email():
    """
    Internal route for testing email configuration.
    Sends a test email to verify SMTP settings.
    """
    try:
        recipient = request.args.get('recipient', current_app.config.get('EMAIL_USERNAME'))
        
        if not recipient:
            return jsonify({
                'status': 'error',
                'message': 'No recipient specified and EMAIL_USERNAME not configured'
            }), 400
        
        # Check if email is configured
        smtp_server = current_app.config.get('SMTP_SERVER')
        smtp_port = current_app.config.get('SMTP_PORT')
        email_username = current_app.config.get('EMAIL_USERNAME')
        email_password = current_app.config.get('EMAIL_PASSWORD')
        
        if not all([smtp_server, smtp_port, email_username, email_password]):
            return jsonify({
                'status': 'error',
                'message': 'Email not fully configured',
                'config': {
                    'smtp_server': bool(smtp_server),
                    'smtp_port': bool(smtp_port),
                    'email_username': bool(email_username),
                    'email_password': bool(email_password)
                }
            }), 400
        
        # Send test email
        subject = "OpsDeck - Test Email"
        body = f"""
        <h2>Email Configuration Test</h2>
        <p>This is a test email from OpsDeck to verify SMTP configuration.</p>
        <p><strong>Timestamp:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        <p><strong>SMTP Server:</strong> {smtp_server}:{smtp_port}</p>
        <p>If you received this email, your email configuration is working correctly.</p>
        """
        
        notifications.send_email(
            current_app._get_current_object(),
            subject,
            body,
            [recipient]
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Test email sent successfully',
            'recipient': recipient,
            'smtp_server': smtp_server,
            'smtp_port': smtp_port
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Failed to send test email',
            'error': str(e)
        }), 500


@main_bp.route('/internal/health-check')
def internal_health_check():
    """
    Internal route for comprehensive health check.
    Tests database, storage, scheduler, and email configuration.
    """
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'components': {}
    }
    
    all_healthy = True
    
    # 1. Database Check
    try:
        user_count = User.query.count()
        health_status['components']['database'] = {
            'status': 'healthy',
            'type': 'PostgreSQL' if current_app.config.get('IS_POSTGRES') else 'SQLite',
            'user_count': user_count
        }
    except Exception as e:
        all_healthy = False
        health_status['components']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    # 2. File Storage Check
    try:
        upload_folder = current_app.config.get('UPLOAD_FOLDER')
        if upload_folder and os.path.exists(upload_folder):
            # Test write permissions
            test_file = os.path.join(upload_folder, '.health_check_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            
            health_status['components']['storage'] = {
                'status': 'healthy',
                'upload_folder': upload_folder,
                'writable': True
            }
        else:
            all_healthy = False
            health_status['components']['storage'] = {
                'status': 'unhealthy',
                'error': 'Upload folder does not exist',
                'upload_folder': upload_folder
            }
    except Exception as e:
        all_healthy = False
        health_status['components']['storage'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    # 3. Scheduler Check (only if not in testing mode)
    if not current_app.config.get('TESTING'):
        health_status['components']['scheduler'] = {
            'status': 'configured',
            'note': 'Scheduler is enabled (not in testing mode)'
        }
    else:
        health_status['components']['scheduler'] = {
            'status': 'disabled',
            'note': 'Scheduler disabled in testing mode'
        }
    
    # 4. Email Configuration Check
    smtp_server = current_app.config.get('SMTP_SERVER')
    smtp_port = current_app.config.get('SMTP_PORT')
    email_username = current_app.config.get('EMAIL_USERNAME')
    email_password = current_app.config.get('EMAIL_PASSWORD')
    
    if all([smtp_server, smtp_port, email_username, email_password]):
        health_status['components']['email'] = {
            'status': 'configured',
            'smtp_server': smtp_server,
            'smtp_port': smtp_port
        }
    else:
        health_status['components']['email'] = {
            'status': 'not_configured',
            'note': 'Email settings incomplete'
        }
    
    # Set overall status
    if not all_healthy:
        health_status['status'] = 'unhealthy'
        return jsonify(health_status), 503
    
    return jsonify(health_status), 200


@main_bp.route('/internal/test-security')
def internal_test_security():
    """
    Internal route for security configuration audit.
    Checks security settings and provides recommendations.
    """
    audit_results = {
        'status': 'success',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {},
        'warnings': [],
        'recommendations': []
    }
    
    # 1. Check SECRET_KEY
    secret_key = current_app.config.get('SECRET_KEY', '')
    if secret_key in ['your-secret-key-change-this', 'dev', 'development', '']:
        audit_results['checks']['secret_key'] = {
            'status': 'warning',
            'message': 'Using default or weak SECRET_KEY'
        }
        audit_results['warnings'].append('SECRET_KEY is using a default or weak value')
        audit_results['recommendations'].append('Set a strong SECRET_KEY in environment variables')
    elif len(secret_key) < 32:
        audit_results['checks']['secret_key'] = {
            'status': 'warning',
            'message': 'SECRET_KEY is too short (< 32 characters)'
        }
        audit_results['warnings'].append('SECRET_KEY should be at least 32 characters')
    else:
        audit_results['checks']['secret_key'] = {
            'status': 'ok',
            'message': 'SECRET_KEY is configured properly'
        }
    
    # 2. Check MFA
    mfa_enabled = current_app.config.get('MFA_ENABLED', False)
    audit_results['checks']['mfa'] = {
        'status': 'info',
        'enabled': mfa_enabled,
        'message': 'MFA is enabled' if mfa_enabled else 'MFA is disabled'
    }
    if not mfa_enabled:
        audit_results['recommendations'].append('Consider enabling MFA for enhanced security')
    
    # 3. Check HTTPS/Talisman
    is_development = current_app.debug or os.environ.get('FLASK_ENV') == 'development'
    audit_results['checks']['https'] = {
        'status': 'info',
        'force_https': not is_development,
        'message': 'HTTPS enforced' if not is_development else 'HTTPS not enforced (development mode)'
    }
    
    # 4. Check CSRF Protection
    csrf_enabled = 'csrf' in current_app.extensions
    audit_results['checks']['csrf'] = {
        'status': 'ok' if csrf_enabled else 'warning',
        'enabled': csrf_enabled,
        'message': 'CSRF protection enabled' if csrf_enabled else 'CSRF protection not found'
    }
    if not csrf_enabled:
        audit_results['warnings'].append('CSRF protection is not enabled')
    
    # 5. Check for default admin password
    default_admin_email = current_app.config.get('DEFAULT_ADMIN_EMAIL', 'admin@example.com')
    default_admin_password = current_app.config.get('DEFAULT_ADMIN_INITIAL_PASSWORD', 'admin123')
    
    try:
        admin_user = User.query.filter_by(email=default_admin_email).first()
        if admin_user and admin_user.check_password(default_admin_password):
            audit_results['checks']['default_admin'] = {
                'status': 'critical',
                'message': 'Default admin password is still in use'
            }
            audit_results['warnings'].append('CRITICAL: Default admin password has not been changed')
            audit_results['recommendations'].append('Change the default admin password immediately')
        else:
            audit_results['checks']['default_admin'] = {
                'status': 'ok',
                'message': 'Default admin password has been changed or admin user not found'
            }
    except Exception as e:
        audit_results['checks']['default_admin'] = {
            'status': 'error',
            'message': f'Could not check admin password: {str(e)}'
        }
    
    # 6. Check database type (SQLite in production is a warning)
    is_postgres = current_app.config.get('IS_POSTGRES', False)
    audit_results['checks']['database'] = {
        'status': 'ok' if is_postgres else 'info',
        'type': 'PostgreSQL' if is_postgres else 'SQLite',
        'message': 'Using PostgreSQL' if is_postgres else 'Using SQLite'
    }
    if not is_postgres and not is_development:
        audit_results['recommendations'].append('Consider using PostgreSQL for production deployments')
    
    # Calculate security score
    critical_issues = len([w for w in audit_results['warnings'] if 'CRITICAL' in w])
    warnings = len(audit_results['warnings']) - critical_issues
    
    audit_results['summary'] = {
        'critical_issues': critical_issues,
        'warnings': warnings,
        'recommendations': len(audit_results['recommendations'])
    }
    
    return jsonify(audit_results), 200
