"""
Campaign Routes

CRUD and management for mass communication campaigns.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from ..extensions import db
from ..models import User, Group
from ..models.communications import Campaign, ScheduledCommunication
from ..routes.admin import admin_required
from ..routes.main import login_required

campaigns_bp = Blueprint('campaigns', __name__)


# ==========================================
# CAMPAIGN CRUD
# ==========================================

@campaigns_bp.route('/')
@login_required
@admin_required
def list_campaigns():
    """List all campaigns with their status."""
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    return render_template('campaigns/list.html', campaigns=campaigns)


@campaigns_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_campaign():
    """Create a new campaign (wizard form)."""
    if request.method == 'POST':
        title = request.form.get('title')
        subject = request.form.get('subject')
        body_html = request.form.get('body_html')
        send_to_all = request.form.get('send_to_all') == 'on'
        scheduled_at_str = request.form.get('scheduled_at')
        user_ids = request.form.getlist('user_ids')
        group_ids = request.form.getlist('group_ids')
        
        if not title or not subject or not body_html:
            flash('Title, subject, and body are required.', 'danger')
            return redirect(url_for('campaigns.new_campaign'))
        
        # Parse scheduled_at if provided
        scheduled_at = None
        if scheduled_at_str:
            try:
                scheduled_at = datetime.strptime(scheduled_at_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid date/time format.', 'danger')
                return redirect(url_for('campaigns.new_campaign'))
        
        # Create campaign
        campaign = Campaign(
            title=title,
            subject=subject,
            body_html=body_html,
            send_to_all=send_to_all,
            scheduled_at=scheduled_at,
            created_by_id=session.get('user_id'),
            status='draft'
        )
        
        # Add target users
        if user_ids and not send_to_all:
            users = User.query.filter(User.id.in_([int(i) for i in user_ids])).all()
            campaign.target_users = users
        
        # Add target groups
        if group_ids and not send_to_all:
            groups = Group.query.filter(Group.id.in_([int(i) for i in group_ids])).all()
            campaign.target_groups = groups
        
        db.session.add(campaign)
        db.session.commit()
        
        flash(f'Campaign "{title}" created as draft.', 'success')
        return redirect(url_for('campaigns.detail', id=campaign.id))
    
    # GET - show form
    users = User.query.filter_by(is_archived=False).order_by(User.name).all()
    groups = Group.query.order_by(Group.name).all()
    return render_template('campaigns/form.html', campaign=None, users=users, groups=groups)


@campaigns_bp.route('/<int:id>')
@login_required
@admin_required
def detail(id):
    """Campaign detail/report view."""
    campaign = Campaign.query.get_or_404(id)
    
    # Get scheduled communications for this campaign
    communications = ScheduledCommunication.query.filter_by(
        target_type='campaign', target_id=id
    ).order_by(ScheduledCommunication.recipient_name).all()
    
    stats = campaign.get_communications_stats()
    
    return render_template('campaigns/detail.html', 
                           campaign=campaign, 
                           communications=communications,
                           stats=stats)


@campaigns_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_campaign(id):
    """Edit a draft campaign."""
    campaign = Campaign.query.get_or_404(id)
    
    if campaign.status != 'draft':
        flash('Only draft campaigns can be edited.', 'warning')
        return redirect(url_for('campaigns.detail', id=id))
    
    if request.method == 'POST':
        campaign.title = request.form.get('title')
        campaign.subject = request.form.get('subject')
        campaign.body_html = request.form.get('body_html')
        campaign.send_to_all = request.form.get('send_to_all') == 'on'
        
        scheduled_at_str = request.form.get('scheduled_at')
        if scheduled_at_str:
            try:
                campaign.scheduled_at = datetime.strptime(scheduled_at_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        else:
            campaign.scheduled_at = None
        
        # Update target users
        user_ids = request.form.getlist('user_ids')
        if not campaign.send_to_all:
            users = User.query.filter(User.id.in_([int(i) for i in user_ids])).all() if user_ids else []
            campaign.target_users = users
        
        # Update target groups
        group_ids = request.form.getlist('group_ids')
        if not campaign.send_to_all:
            groups = Group.query.filter(Group.id.in_([int(i) for i in group_ids])).all() if group_ids else []
            campaign.target_groups = groups
        
        db.session.commit()
        flash('Campaign updated.', 'success')
        return redirect(url_for('campaigns.detail', id=id))
    
    users = User.query.filter_by(is_archived=False).order_by(User.name).all()
    groups = Group.query.order_by(Group.name).all()
    return render_template('campaigns/form.html', campaign=campaign, users=users, groups=groups)


@campaigns_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_campaign(id):
    """Delete a campaign and its scheduled communications."""
    campaign = Campaign.query.get_or_404(id)
    
    # Delete all associated scheduled communications
    ScheduledCommunication.query.filter_by(
        target_type='campaign', target_id=id
    ).delete()
    
    title = campaign.title
    db.session.delete(campaign)
    db.session.commit()
    
    flash(f'Campaign "{title}" deleted.', 'success')
    return redirect(url_for('campaigns.list_campaigns'))


# ==========================================
# CAMPAIGN ACTIONS
# ==========================================

@campaigns_bp.route('/<int:id>/schedule', methods=['POST'])
@login_required
@admin_required
def schedule_campaign(id):
    """
    Schedule/launch a campaign.
    This spawns individual ScheduledCommunication records for each recipient.
    """
    campaign = Campaign.query.get_or_404(id)
    
    if campaign.status != 'draft':
        flash('Campaign has already been scheduled or processed.', 'warning')
        return redirect(url_for('campaigns.detail', id=id))
    
    # Resolve audience
    audience = campaign.get_resolved_audience()
    
    if not audience:
        flash('No recipients found. Add users, groups, or enable "Send to All".', 'danger')
        return redirect(url_for('campaigns.detail', id=id))
    
    # Determine scheduled date
    if campaign.scheduled_at:
        scheduled_date = campaign.scheduled_at.date()
    else:
        scheduled_date = datetime.utcnow().date()
    
    # Spawn communications
    created_count = 0
    for user in audience:
        comm = ScheduledCommunication(
            template_id=None,  # Campaign uses inline content
            target_type='campaign',
            target_id=campaign.id,
            scheduled_date=scheduled_date,
            recipient_email=user.email,
            recipient_name=user.name,
            recipient_user_id=user.id,
            recipient_type='target_user',
            status='pending'
        )
        db.session.add(comm)
        created_count += 1
    
    # Update campaign status
    campaign.status = 'scheduled'
    campaign.processed_at = datetime.utcnow()
    
    db.session.commit()
    
    flash(f'Campaign scheduled! {created_count} emails queued for delivery.', 'success')
    return redirect(url_for('campaigns.detail', id=id))


@campaigns_bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
@admin_required
def cancel_campaign(id):
    """
    🚨 PANIC BUTTON: Cancel all pending communications for this campaign.
    """
    campaign = Campaign.query.get_or_404(id)
    
    # Mass cancel pending communications
    cancelled_count = ScheduledCommunication.query.filter_by(
        target_type='campaign',
        target_id=id,
        status='pending'
    ).update({'status': 'cancelled'})
    
    db.session.commit()
    
    if cancelled_count > 0:
        flash(f'🛑 {cancelled_count} pending emails cancelled.', 'warning')
    else:
        flash('No pending emails to cancel.', 'info')
    
    return redirect(url_for('campaigns.detail', id=id))


@campaigns_bp.route('/<int:id>/send_now', methods=['POST'])
@login_required
@admin_required
def send_campaign_now(id):
    """
    Force immediate processing of a scheduled campaign.
    Triggers the sending of all pending communications right now.
    """
    from ..utils.communications_context import get_template_context, render_email_template
    from .. import notifications
    from flask import current_app
    
    campaign = Campaign.query.get_or_404(id)
    
    # Get pending communications
    pending = ScheduledCommunication.query.filter_by(
        target_type='campaign',
        target_id=id,
        status='pending'
    ).all()
    
    if not pending:
        flash('No pending emails to send.', 'info')
        return redirect(url_for('campaigns.detail', id=id))
    
    sent_count = 0
    failed_count = 0
    
    for comm in pending:
        try:
            context = get_template_context(comm)
            subject, body_html = render_email_template(campaign, context)
            
            success = notifications.send_email(
                current_app._get_current_object(),
                subject,
                body_html,
                [comm.recipient_email]
            )
            
            if success:
                comm.status = 'sent'
                comm.sent_at = datetime.utcnow()
                sent_count += 1
            else:
                comm.status = 'failed'
                comm.error_message = 'Email sending failed'
                failed_count += 1
                
        except Exception as e:
            comm.status = 'failed'
            comm.error_message = str(e)[:500]
            failed_count += 1
    
    db.session.commit()
    
    flash(f'Sent {sent_count} emails, {failed_count} failed.', 'success' if failed_count == 0 else 'warning')
    return redirect(url_for('campaigns.detail', id=id))
