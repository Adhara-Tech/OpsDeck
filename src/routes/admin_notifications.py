"""
Admin Notifications Blueprint

Provides an admin interface for managing system notification events.
Allows admins to enable/disable notifications and change templates.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..extensions import db
from ..models.notifications import NotificationEvent
from ..models.communications import EmailTemplate
from .main import login_required
from .admin import admin_required

admin_notifications_bp = Blueprint('admin_notifications', __name__)


@admin_notifications_bp.route('/')
@login_required
@admin_required
def list_events():
    """List all notification events with their current configuration."""
    events = NotificationEvent.query.order_by(NotificationEvent.name).all()
    templates = EmailTemplate.query.filter_by(is_active=True).order_by(EmailTemplate.name).all()
    return render_template('admin/notifications.html', events=events, templates=templates)


@admin_notifications_bp.route('/<int:event_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_event(event_id):
    """Toggle a notification event on/off."""
    event = NotificationEvent.query.get_or_404(event_id)
    event.enabled = not event.enabled
    db.session.commit()
    
    status = 'enabled' if event.enabled else 'disabled'
    flash(f'Notification "{event.name}" has been {status}.', 'success')
    return redirect(url_for('admin_notifications.list_events'))


@admin_notifications_bp.route('/<int:event_id>/update', methods=['POST'])
@login_required
@admin_required
def update_event(event_id):
    """Update a notification event's template and days offset."""
    event = NotificationEvent.query.get_or_404(event_id)
    
    # Update template
    template_id = request.form.get('template_id')
    if template_id:
        event.template_id = int(template_id) if template_id != '' else None
    else:
        event.template_id = None
    
    # Update days offset
    days_offset = request.form.get('days_offset')
    if days_offset:
        try:
            event.days_offset = int(days_offset)
        except ValueError:
            flash('Invalid days offset value.', 'danger')
            return redirect(url_for('admin_notifications.list_events'))
    
    db.session.commit()
    flash(f'Notification "{event.name}" has been updated.', 'success')
    return redirect(url_for('admin_notifications.list_events'))
