import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Import the models needed for the notification logic
from .models import Subscription, NotificationSetting
from .models.credentials import Credential, CredentialSecret
from .models.certificates import Certificate, CertificateVersion
from .models.communications import ScheduledCommunication

# --- Notification Functions ---

def send_email(app, subject, body, to_emails):
    """Send email notification using app config."""
    # Check for both a recipient and an email username in config
    if not to_emails or not app.config.get('EMAIL_USERNAME'):
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['EMAIL_USERNAME']
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(app.config['SMTP_SERVER'], app.config['SMTP_PORT'])
        server.starttls()
        server.login(app.config['EMAIL_USERNAME'], app.config['EMAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()
        app.logger.info(f"Sent renewal email to {to_emails}")
        return True
    except Exception as e:
        app.logger.error(f"Failed to send email: {e}")
        return False

def send_webhook(app, url, data):
    """Send webhook notification to a specific URL."""
    if not url:
        return False
    
    try:
        response = requests.post(url, json=data, timeout=10)
        app.logger.info(f"Sent webhook to {url}, status code: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        app.logger.error(f"Failed to send webhook: {e}")
        return False

def check_upcoming_renewals(app):
    """
    Checks for subscriptions that need renewal notifications based on user settings
    and sends alerts via email and/or webhooks.
    """
    with app.app_context():
        # Step 1: Fetch Notification Settings from the database
        settings = NotificationSetting.query.first()
        if not settings or (not settings.email_enabled and not settings.webhook_enabled):
            app.logger.info("Notifications are disabled. Skipping check.")
            return

        # Step 2: Determine which days require notifications
        try:
            notify_days = {int(day) for day in settings.notify_days_before.split(',') if day}
        except (ValueError, TypeError):
            app.logger.error("Invalid 'notify_days_before' format. Skipping check.")
            return
            
        if not notify_days:
            return # No notification days configured

        # Step 3: Find subscriptions that match the notification criteria
        today = datetime.now().date()
        subscriptions_to_notify = []
        all_subscriptions = Subscription.query.all()

        for subscription in all_subscriptions:
            days_until = (subscription.next_renewal_date - today).days
            # Check if the subscription is due on one of the configured notification days
            if days_until in notify_days:
                subscriptions_to_notify.append(subscription)

        # Step 4: If there are subscriptions to notify about, build and send the alerts
        if subscriptions_to_notify:
            html_content = "<h2>Upcoming subscription Renewals</h2><ul>"
            webhook_data = {
                "text": "Upcoming subscription Renewals",
                "renewals": []
            }
            
            for subscription in subscriptions_to_notify:
                days_until = (subscription.next_renewal_date - today).days
                html_content += f"<li><strong>{subscription.name}</strong> ({subscription.subscription_type}) - Renews in {days_until} days - €{subscription.cost_eur:.2f}</li>"
                webhook_data["renewals"].append({
                    "name": subscription.name,
                    "type": subscription.subscription_type,
                    "renewal_date": subscription.next_renewal_date.isoformat(),
                    "days_until": days_until,
                    "cost_eur": subscription.cost_eur
                })
            
            html_content += "</ul>"
            
            # Send email if enabled and a recipient is set
            if settings.email_enabled and settings.email_recipient:
                send_email(
                    app,
                    "Subscription Renewal Reminder", 
                    html_content,
                    [settings.email_recipient]
                )
            
            # Send webhook if enabled and a URL is set
            if settings.webhook_enabled and settings.webhook_url:
                send_webhook(app, settings.webhook_url, webhook_data)
        else:
            app.logger.info("No subscriptions require notification today.")

def check_credential_expirations(app):
    """
    Checks for credentials with active secrets expiring soon and sends 
    notifications to owners at 30, 14, and 7 days before expiry.
    """
    with app.app_context():
        # Notification thresholds (days before expiry)
        NOTIFY_DAYS = [30, 14, 7]
        
        today = datetime.now().date()
        credentials_to_notify = []
        
        # Query all active secrets with expiry dates
        active_secrets = CredentialSecret.query.filter(
            CredentialSecret.is_active == True,
            CredentialSecret.expires_at.isnot(None)
        ).all()
        
        # Check each secret for notification threshold
        for secret in active_secrets:
            days_until_expiry = (secret.expires_at.date() - today).days
            
            # Only notify on specific days (30, 14, 7)
            if days_until_expiry in NOTIFY_DAYS:
                credential = secret.credential
                credentials_to_notify.append({
                    'credential': credential,
                    'secret': secret,
                    'days_until_expiry': days_until_expiry
                })
        
        # Send notifications if any credentials are expiring
        if credentials_to_notify:
            # Group by owner for consolidated emails
            notifications_by_owner = {}
            
            for item in credentials_to_notify:
                credential = item['credential']
                owner = credential.owner
                
                if not owner or not owner.email:
                    app.logger.warning(f"Credential '{credential.name}' has no valid owner email")
                    continue
                
                if owner.email not in notifications_by_owner:
                    notifications_by_owner[owner.email] = {
                        'owner_name': owner.name,
                        'credentials': []
                    }
                
                notifications_by_owner[owner.email]['credentials'].append(item)
            
            # Send email to each owner
            for email, data in notifications_by_owner.items():
                html_content = f"""
                <h2>Credential Expiration Alert</h2>
                <p>Hello {data['owner_name']},</p>
                <p>The following credentials under your ownership are expiring soon:</p>
                <ul>
                """
                
                for item in data['credentials']:
                    cred = item['credential']
                    secret = item['secret']
                    days = item['days_until_expiry']
                    
                    # Determine urgency level
                    urgency = "⚠️ URGENT" if days <= 7 else "⚡ WARNING" if days <= 14 else "ℹ️ NOTICE"
                    
                    # Build credential description
                    target = cred.target_name if cred.target_name != "N/A" else "No linked service"
                    
                    html_content += f"""
                    <li>
                        <strong>{urgency} - {cred.name}</strong> ({cred.type})<br>
                        Target: {target}<br>
                        Masked Value: <code>{secret.masked_value}</code><br>
                        Expires: {secret.expires_at.strftime('%Y-%m-%d')} ({days} days remaining)<br>
                        {'<span style="color: red;">⚠️ CRITICAL INFRASTRUCTURE</span><br>' if cred.break_glass else ''}
                        <em>Please rotate this credential as soon as possible.</em>
                    </li>
                    """
                
                html_content += """
                </ul>
                <p>To rotate a credential, visit the OpsDeck Credentials section and use the "Rotate Secret" button.</p>
                <p><strong>Security Reminder:</strong> Never share your credentials or store them in plain text.</p>
                """
                
                # Send the email
                success = send_email(
                    app,
                    f"Credential Expiration Alert - {len(data['credentials'])} credential(s) expiring soon",
                    html_content,
                    [email]
                )
                
                if success:
                    app.logger.info(f"Sent credential expiration notification to {email} for {len(data['credentials'])} credential(s)")
                else:
                    app.logger.error(f"Failed to send credential expiration notification to {email}")
        else:
            app.logger.info("No credentials require expiration notification today.")

def check_certificate_expirations(app):
    """
    Checks for active certificates expiring soon and sends 
    notifications to owners at 30, 7, and 1 days before expiry.
    """
    with app.app_context():
        # Notification thresholds (days before expiry)
        NOTIFY_DAYS = [30, 7, 1]
        
        today = datetime.now().date()
        certificates_to_notify = []
        
        # Query all active certificate versions using the CertificateVersion model directly
        # We need versions that are marked is_active=True
        active_versions = CertificateVersion.query.filter(
            CertificateVersion.is_active == True,
            CertificateVersion.expires_at.isnot(None)
        ).all()
        
        # Check each version for notification threshold
        for version in active_versions:
            days_until_expiry = (version.expires_at - today).days
            
            # Only notify on specific days
            if days_until_expiry in NOTIFY_DAYS:
                cert = version.certificate
                certificates_to_notify.append({
                    'certificate': cert,
                    'version': version,
                    'days_until_expiry': days_until_expiry
                })
        
        # Send notifications
        if certificates_to_notify:
            # Group by owner
            notifications_by_owner = {}
            
            for item in certificates_to_notify:
                cert = item['certificate']
                owner = cert.owner
                
                # Check for valid owner email
                if not owner or not getattr(owner, 'email', None):
                    app.logger.warning(f"Certificate '{cert.name}' has no valid owner email")
                    continue
                
                if owner.email not in notifications_by_owner:
                    notifications_by_owner[owner.email] = {
                        'owner_name': owner.name,
                        'certificates': []
                    }
                
                notifications_by_owner[owner.email]['certificates'].append(item)
            
            # Send email to each owner
            for email, data in notifications_by_owner.items():
                html_content = f"""
                <h2>Certificate Expiration Alert</h2>
                <p>Hello {data['owner_name']},</p>
                <p>The following digital certificates under your ownership are expiring soon:</p>
                <ul>
                """
                
                for item in data['certificates']:
                    cert = item['certificate']
                    version = item['version']
                    days = item['days_until_expiry']
                    
                    # Determine urgency
                    urgency = "⚠️ URGENT" if days <= 7 else "ℹ️ NOTICE"
                    
                    html_content += f"""
                    <li>
                        <strong>{urgency} - {cert.name}</strong> ({cert.type})<br>
                        Common Name: <code>{version.common_name or 'N/A'}</code><br>
                        Expires: {version.expires_at.strftime('%Y-%m-%d')} ({days} days remaining)<br>
                        <em>Please renew this certificate to prevent service interruption.</em>
                    </li>
                    """
                
                html_content += """
                </ul>
                <p>Visit OpsDeck Certificates to manage renewals.</p>
                """
                
                # Send the email
                success = send_email(
                    app,
                    f"Certificate Expiration Alert - {len(data['certificates'])} expiring",
                    html_content,
                    [email]
                )
                
                if success:
                    app.logger.info(f"Sent certificate expiration notification to {email}")
                else:
                    app.logger.error(f"Failed to send certificate expiration notification to {email}")
        else:
            app.logger.info("No certificates require expiration notification today.")


def process_communications_queue(app):
    """
    Process pending scheduled communications.
    Called by the background scheduler (daily or hourly).
    Sends emails that are due and updates their status.
    """
    from .extensions import db
    from .utils.communications_context import get_template_context, render_email_template
    
    with app.app_context():
        today = datetime.now().date()
        
        # Query pending communications that are due (scheduled_date <= today)
        pending_comms = ScheduledCommunication.query.filter(
            ScheduledCommunication.status == 'pending',
            ScheduledCommunication.scheduled_date <= today
        ).all()
        
        if not pending_comms:
            app.logger.info("Communications queue: No pending communications to process.")
            return
        
        app.logger.info(f"Communications queue: Processing {len(pending_comms)} pending communication(s).")
        
        sent_count = 0
        failed_count = 0
        
        for comm in pending_comms:
            # Skip if no recipient email
            if not comm.recipient_email:
                app.logger.warning(f"Communication {comm.id}: No recipient email, skipping.")
                continue
            
            # Skip if template is inactive
            if not comm.template or not comm.template.is_active:
                app.logger.warning(f"Communication {comm.id}: Template inactive or missing, skipping.")
                continue
            
            try:
                # Get context and render template
                context = get_template_context(comm)
                subject, body_html = render_email_template(comm.template, context)
                
                # Send email
                success = send_email(
                    app,
                    subject,
                    body_html,
                    [comm.recipient_email]
                )
                
                if success:
                    comm.status = 'sent'
                    comm.sent_at = datetime.utcnow()
                    sent_count += 1
                    app.logger.info(f"Communication {comm.id}: Sent to {comm.recipient_email}")
                else:
                    comm.status = 'failed'
                    comm.error_message = 'Email sending failed - check SMTP configuration'
                    comm.retry_count += 1
                    failed_count += 1
                    app.logger.error(f"Communication {comm.id}: Failed to send")
                    
            except Exception as e:
                comm.status = 'failed'
                comm.error_message = str(e)[:500]  # Limit error message length
                comm.retry_count += 1
                failed_count += 1
                app.logger.error(f"Communication {comm.id}: Error - {str(e)}")
        
        # Commit all status changes
        db.session.commit()
        
        app.logger.info(f"Communications queue: Processed {len(pending_comms)} - Sent: {sent_count}, Failed: {failed_count}")