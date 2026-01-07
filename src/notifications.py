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
    Checks for subscriptions and licenses that need renewal/expiry notifications.
    Instead of sending emails directly, queues messages via ScheduledCommunication
    for the dispatcher to process every 5 minutes.
    """
    from .extensions import db
    from .models.notifications import NotificationEvent
    from .models.communications import ScheduledCommunication
    from .models.assets import License
    from .models.auth import User
    
    with app.app_context():
        today = datetime.now().date()
        queued_count = 0
        
        # ============================================================
        # 1. LICENSE EXPIRING NOTIFICATIONS
        # ============================================================
        license_event = NotificationEvent.query.filter_by(
            event_code='LICENSE_EXPIRING'
        ).first()
        
        if license_event and license_event.enabled and license_event.template_id:
            days_before = license_event.days_offset or 7
            target_date = today + __import__('datetime').timedelta(days=days_before)
            
            # Find licenses expiring on the target date
            expiring_licenses = License.query.filter(
                License.expiry_date == target_date,
                License.is_archived == False
            ).all()
            
            for license in expiring_licenses:
                # Get the owner (assigned user) for the notification
                owner = User.query.get(license.user_id) if license.user_id else None
                if not owner or not owner.email:
                    app.logger.warning(f"License {license.id} has no owner email, skipping notification.")
                    continue
                
                # Get configured channels (default to email only)
                channels = license_event.channels or ['email']
                
                for channel in channels:
                    # Check if we already queued this notification for this channel (avoid duplicates)
                    existing = ScheduledCommunication.query.filter_by(
                        target_type='license',
                        target_id=license.id,
                        channel=channel,
                        status='pending'
                    ).first()
                    
                    if existing:
                        continue
                    
                    # Create the scheduled communication for this channel
                    comm = ScheduledCommunication(
                        template_id=license_event.template_id,
                        status='pending',
                        scheduled_date=today,  # Send immediately on next dispatcher run
                        target_type='license',
                        target_id=license.id,
                        recipient_email=owner.email,
                        recipient_name=owner.name,
                        recipient_type='owner',
                        recipient_user_id=owner.id,
                        channel=channel,
                        slack_target_channel=license_event.slack_target_channel if channel == 'slack' else None
                    )
                    db.session.add(comm)
                    queued_count += 1
                    app.logger.info(f"Queued license expiry notification ({channel}) for license {license.id} ({license.name})")
        
        # ============================================================
        # 2. SUBSCRIPTION RENEWAL NOTIFICATIONS
        # ============================================================
        subscription_event = NotificationEvent.query.filter_by(
            event_code='SUBSCRIPTION_RENEWAL'
        ).first()
        
        if subscription_event and subscription_event.enabled and subscription_event.template_id:
            days_before = subscription_event.days_offset or 7
            
            # Find subscriptions renewing within the configured days
            all_subscriptions = Subscription.query.all()
            
            for subscription in all_subscriptions:
                try:
                    renewal_date = subscription.next_renewal_date
                    if not renewal_date:
                        continue
                    
                    days_until = (renewal_date - today).days
                    
                    if days_until == days_before:
                        # Get notification settings recipient for subscription alerts
                        settings = NotificationSetting.query.first()
                        if not settings or not settings.email_recipient:
                            continue
                        
                        # Get configured channels (default to email only)
                        channels = subscription_event.channels or ['email']
                        
                        for channel in channels:
                            # Check if we already queued this notification for this channel
                            existing = ScheduledCommunication.query.filter_by(
                                target_type='subscription',
                                target_id=subscription.id,
                                channel=channel,
                                status='pending'
                            ).first()
                            
                            if existing:
                                continue
                            
                            # Create the scheduled communication for this channel
                            comm = ScheduledCommunication(
                                template_id=subscription_event.template_id,
                                status='pending',
                                scheduled_date=today,
                                target_type='subscription',
                                target_id=subscription.id,
                                recipient_email=settings.email_recipient,
                                recipient_name='Admin',
                                recipient_type='admin',
                                channel=channel,
                                slack_target_channel=subscription_event.slack_target_channel if channel == 'slack' else None
                            )
                            db.session.add(comm)
                            queued_count += 1
                            app.logger.info(f"Queued subscription renewal notification ({channel}) for {subscription.name}")
                except Exception as e:
                    app.logger.error(f"Error checking subscription {subscription.id}: {e}")
        
        # Commit all queued communications
        if queued_count > 0:
            db.session.commit()
            app.logger.info(f"Queued {queued_count} renewal notification(s) for processing.")
        else:
            app.logger.info("No renewal notifications to queue today.")

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
    Called by the background scheduler every 5 minutes.
    Sends emails, Slack messages, or webhooks that are due and updates their status.
    Processes in batches of 50 to prevent blocking during high-volume periods.
    Uses database-level row locking (FOR UPDATE SKIP LOCKED) for concurrent safety.
    """
    from .extensions import db
    from .utils.communications_context import get_template_context, render_email_template
    from .models.communications import Campaign
    
    BATCH_SIZE = 50
    
    with app.app_context():
        now = datetime.utcnow()
        today = now.date()
        
        # Query pending communications that are due (scheduled_date <= today)
        # Also respect exponential backoff: only pick up if next_retry_at is null or has passed
        # Use FOR UPDATE SKIP LOCKED for concurrent safety - prevents duplicate sends
        # when multiple workers/containers process the queue simultaneously
        from sqlalchemy import or_
        
        pending_comms = db.session.query(ScheduledCommunication).filter(
            ScheduledCommunication.status == 'pending',
            ScheduledCommunication.scheduled_date <= today,
            or_(
                ScheduledCommunication.next_retry_at.is_(None),
                ScheduledCommunication.next_retry_at <= now
            )
        ).with_for_update(skip_locked=True).limit(BATCH_SIZE).all()
        
        if not pending_comms:
            app.logger.info("Communications queue: No pending communications to process.")
            return
        
        app.logger.info(f"Communications queue: Processing batch of {len(pending_comms)} pending communication(s).")
        
        sent_count = 0
        failed_count = 0
        
        # Lazy-load Slack service only if needed
        slack_service = None
        
        for comm in pending_comms:
            # Skip if no recipient email (needed for both email and Slack lookup)
            if not comm.recipient_email:
                app.logger.warning(f"Communication {comm.id}: No recipient email, skipping.")
                continue
            
            # Determine the template source based on target type
            if comm.target_type == 'campaign':
                # For campaigns, load the Campaign object which has inline subject/body
                template_source = Campaign.query.get(comm.target_id)
                if not template_source:
                    app.logger.warning(f"Communication {comm.id}: Campaign not found, skipping.")
                    continue
            else:
                # For other types, use the linked EmailTemplate
                if not comm.template or not comm.template.is_active:
                    app.logger.warning(f"Communication {comm.id}: Template inactive or missing, skipping.")
                    continue
                template_source = comm.template
            
            try:
                # Get context and render template
                context = get_template_context(comm)
                subject, body_html = render_email_template(template_source, context)
                
                # Dispatch based on channel type
                channel = getattr(comm, 'channel', 'email') or 'email'
                
                if channel == 'slack':
                    # ============================================
                    # SLACK DISPATCH
                    # ============================================
                    # Lazy-load SlackService for reuse across batch
                    if slack_service is None:
                        from .services.slack_service import SlackService
                        slack_service = SlackService()
                    
                    success = _send_slack_notification(
                        app, comm, subject, body_html, slack_service
                    )
                    
                elif channel == 'webhook':
                    # ============================================
                    # WEBHOOK DISPATCH
                    # ============================================
                    success = _send_webhook_notification(app, comm, subject, body_html)
                    
                else:
                    # ============================================
                    # EMAIL DISPATCH (default)
                    # ============================================
                    success = send_email(
                        app,
                        subject,
                        body_html,
                        [comm.recipient_email]
                    )
                    
                    if not success:
                        comm.error_message = 'Email sending failed - check SMTP configuration'
                
                if success:
                    comm.status = 'sent'
                    comm.sent_at = datetime.utcnow()
                    comm.next_retry_at = None  # Clear any retry scheduling
                    sent_count += 1
                    app.logger.info(f"Communication {comm.id}: Sent via {channel} to {comm.recipient_email}")
                else:
                    # Use exponential backoff retry logic
                    will_retry = comm.mark_for_retry(comm.error_message)
                    failed_count += 1
                    if will_retry:
                        app.logger.warning(f"Communication {comm.id}: Failed via {channel}, scheduled for retry #{comm.retry_count} at {comm.next_retry_at}")
                    else:
                        app.logger.error(f"Communication {comm.id}: Permanently failed after {comm.retry_count} attempts")
                    
            except Exception as e:
                # Check for SlackRateLimitError
                # We use string name check to avoid circular/lazy import issues if not explicitly imported
                if e.__class__.__name__ == 'SlackRateLimitError' or 'SlackRateLimitError' in str(type(e)):
                    app.logger.warning(f"Communication {comm.id}: Slack rate limited. Leaving as pending for next run.")
                    # Keep status='pending' and date as is (will be picked up in next batch)
                    continue

                # Use exponential backoff retry logic
                will_retry = comm.mark_for_retry(str(e)[:500])
                failed_count += 1
                if will_retry:
                    app.logger.warning(f"Communication {comm.id}: Error, scheduled for retry #{comm.retry_count} - {str(e)}")
                else:
                    app.logger.error(f"Communication {comm.id}: Permanently failed after {comm.retry_count} attempts - {str(e)}")
        
        # Commit all status changes
        db.session.commit()
        
        app.logger.info(f"Communications queue: Processed {len(pending_comms)} - Sent: {sent_count}, Failed: {failed_count}")


def _send_slack_notification(app, comm, subject, body_html, slack_service=None):
    """
    Send a notification via Slack.
    
    Args:
        app: Flask app for logging
        comm: ScheduledCommunication instance
        subject: Rendered subject line
        body_html: Rendered HTML body
        slack_service: Optional SlackService instance (will create if None)
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    from .services.slack_service import SlackService, format_slack_notification
    
    if slack_service is None:
        slack_service = SlackService()
    
    if not slack_service.is_configured:
        app.logger.warning(f"Communication {comm.id}: Slack not configured, skipping.")
        comm.error_message = 'Slack not configured (SLACK_BOT_TOKEN missing)'
        return False
    
    # Determine target: fixed channel or DM to user
    target_id = None
    
    if comm.slack_target_channel:
        # Use configured fixed channel (e.g., #devops)
        target_id = comm.slack_target_channel
        app.logger.debug(f"Communication {comm.id}: Using fixed Slack channel {target_id}")
    else:
        # Resolve user ID from email for DM
        target_id = slack_service.resolve_user_by_email(comm.recipient_email)
        if not target_id:
            app.logger.warning(f"Communication {comm.id}: Could not resolve Slack user for {comm.recipient_email}")
            comm.error_message = f'Slack user not found for email: {comm.recipient_email}'
            return False
    
    # Format message for Slack
    # TODO: Generate proper OpsDeck URL based on target_type/target_id
    opsdeck_url = None  # Could be constructed from app config + comm.target_type/target_id
    
    slack_message = format_slack_notification(subject, body_html, opsdeck_url)
    
    # Send the message
    success = slack_service.send_message(target_id, slack_message)
    
    if not success:
        comm.error_message = f'Failed to send Slack message to {target_id}'
    
    return success


def _send_webhook_notification(app, comm, subject, body_html):
    """
    Send a notification via Webhook (HTTP POST with JSON payload).
    
    Args:
        app: Flask app for logging
        comm: ScheduledCommunication instance
        subject: Rendered subject line
        body_html: Rendered HTML body
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    from .models.notifications import NotificationEvent
    
    # Map target_type to event_code for webhook URL lookup
    event_code_map = {
        'license': 'LICENSE_EXPIRING',
        'subscription': 'SUBSCRIPTION_RENEWAL',
        'credential': 'CREDENTIAL_EXPIRING',
        'certificate': 'CERTIFICATE_EXPIRING',
    }
    
    event_code = event_code_map.get(comm.target_type, comm.target_type.upper())
    event = NotificationEvent.query.filter_by(event_code=event_code).first()
    
    webhook_url = event.webhook_url if event else None
    
    if not webhook_url:
        app.logger.warning(f"Communication {comm.id}: No webhook URL configured for {event_code}, skipping.")
        comm.error_message = f'No webhook URL configured for event type: {event_code}'
        return False
    
    # Build structured JSON payload
    payload = {
        'event': event_code,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'communication_id': comm.id,
        'data': {
            'target_type': comm.target_type,
            'target_id': comm.target_id,
            'subject': subject,
            'recipient_email': comm.recipient_email,
            'recipient_name': comm.recipient_name,
        }
    }
    
    success = send_webhook(app, webhook_url, payload)
    
    if not success:
        comm.error_message = f'Webhook delivery failed to: {webhook_url}'
    
    return success