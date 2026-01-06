"""
Admin Communications Routes

CRUD operations for EmailTemplates and PackCommunication management.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..extensions import db
from ..models.communications import EmailTemplate, PackCommunication
from ..routes.admin import admin_required
from ..routes.main import login_required

admin_communications_bp = Blueprint('admin_communications', __name__)


# ==========================================
# EMAIL TEMPLATE CRUD
# ==========================================

@admin_communications_bp.route('/templates')
@login_required
@admin_required
def list_templates():
    """List all email templates."""
    templates = EmailTemplate.query.order_by(EmailTemplate.name).all()
    return render_template('admin/email_templates_list.html', templates=templates)


@admin_communications_bp.route('/templates/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_template():
    """Create a new email template."""
    if request.method == 'POST':
        name = request.form.get('name')
        subject = request.form.get('subject')
        body_html = request.form.get('body_html')
        category = request.form.get('category', 'general')
        
        if not name or not subject or not body_html:
            flash('Name, subject, and body are required.', 'danger')
            return render_template('admin/email_template_form.html', template=None)
        
        # Check for duplicate name
        if EmailTemplate.query.filter_by(name=name).first():
            flash(f'A template named "{name}" already exists.', 'danger')
            return render_template('admin/email_template_form.html', template=None)
        
        template = EmailTemplate(
            name=name,
            subject=subject,
            body_html=body_html,
            category=category
        )
        db.session.add(template)
        db.session.commit()
        
        flash(f'Email template "{name}" created successfully.', 'success')
        return redirect(url_for('admin_communications.list_templates'))
    
    return render_template('admin/email_template_form.html', template=None)


@admin_communications_bp.route('/templates/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_template(id):
    """Edit an existing email template."""
    template = EmailTemplate.query.get_or_404(id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        subject = request.form.get('subject')
        body_html = request.form.get('body_html')
        category = request.form.get('category', 'general')
        is_active = request.form.get('is_active') == 'on'
        
        if not name or not subject or not body_html:
            flash('Name, subject, and body are required.', 'danger')
            return render_template('admin/email_template_form.html', template=template)
        
        # Check if system template (prevent updates)
        if template.is_system:
            flash(f'Cannot edit system template "{template.name}".', 'danger')
            return redirect(url_for('admin_communications.list_templates'))
        
        # Check for duplicate name (excluding current template)
        existing = EmailTemplate.query.filter_by(name=name).first()
        if existing and existing.id != id:
            flash(f'A template named "{name}" already exists.', 'danger')
            return render_template('admin/email_template_form.html', template=template)
        
        template.name = name
        template.subject = subject
        template.body_html = body_html
        template.category = category
        template.is_active = is_active
        
        db.session.commit()
        
        flash(f'Email template "{name}" updated successfully.', 'success')
        return redirect(url_for('admin_communications.list_templates'))
    
    return render_template('admin/email_template_form.html', template=template)


@admin_communications_bp.route('/templates/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_template(id):
    """Delete an email template."""
    template = EmailTemplate.query.get_or_404(id)
    
    # Check if system template

    if template.is_system:
        flash(f'Cannot delete system template "{template.name}".', 'danger')
        return redirect(url_for('admin_communications.list_templates'))

    # Check if template is used in any pack communications
    if template.pack_communications:
        flash(f'Cannot delete template "{template.name}" - it is used in {len(template.pack_communications)} pack communication(s).', 'danger')
        return redirect(url_for('admin_communications.list_templates'))
    
    # Check if template is used in any scheduled communications
    if template.scheduled_communications:
        flash(f'Cannot delete template "{template.name}" - it is used in {len(template.scheduled_communications)} scheduled communication(s).', 'danger')
        return redirect(url_for('admin_communications.list_templates'))
    
    name = template.name
    db.session.delete(template)
    db.session.commit()
    
    flash(f'Email template "{name}" deleted.', 'success')
    return redirect(url_for('admin_communications.list_templates'))


@admin_communications_bp.route('/templates/<int:id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_template(id):
    """Toggle template active status."""
    template = EmailTemplate.query.get_or_404(id)
    
    # Check if system template

    if template.is_system:
        flash(f'Cannot deactivate system template "{template.name}".', 'danger')
        return redirect(url_for('admin_communications.list_templates'))

    template.is_active = not template.is_active
    db.session.commit()
    
    status = 'activated' if template.is_active else 'deactivated'
    flash(f'Email template "{template.name}" {status}.', 'info')
    return redirect(url_for('admin_communications.list_templates'))
