from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify, session
from .main import login_required
from ..extensions import db
from ..models.audits import ComplianceAudit, AuditControlItem, AuditControlLink
from ..models.security import Framework
from ..models.auth import User
from ..models.crm import Contact
from ..models.core import Attachment
from weasyprint import HTML
import io
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

audits_bp = Blueprint('audits', __name__, url_prefix='/security/audits')

# ============================================================================
# LIST & CRUD
# ============================================================================

@audits_bp.route('/')
@login_required
def list_audits():
    audits = ComplianceAudit.query.order_by(ComplianceAudit.created_at.desc()).all()
    return render_template('audits/list.html', audits=audits)

@audits_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_audit():
    if request.method == 'POST':
        name = request.form.get('name')
        framework_id = request.form.get('framework_id')
        auditor_contact_id = request.form.get('auditor_contact_id') or None
        internal_lead_id = request.form.get('internal_lead_id')
        copy_links = request.form.get('copy_links') == 'on'

        if not name or not framework_id or not internal_lead_id:
            flash('Audit Name, Framework, and Internal Lead are required.', 'danger')
            return redirect(url_for('audits.new_audit'))

        try:
            audit = ComplianceAudit.create_snapshot(
                framework_id=int(framework_id),
                name=name,
                auditor_contact_id=int(auditor_contact_id) if auditor_contact_id else None,
                internal_lead_id=int(internal_lead_id),
                copy_links=copy_links
            )
            flash('Audit created successfully.', 'success')
            return redirect(url_for('audits.view_audit', id=audit.id))
        except Exception as e:
            flash(f'Error creating audit: {str(e)}', 'danger')
            return redirect(url_for('audits.new_audit'))

    frameworks = Framework.query.filter_by(is_active=True).all()
    users = User.query.filter_by(is_archived=False).all()
    contacts = Contact.query.filter_by(is_archived=False).all()
    return render_template('audits/new.html', frameworks=frameworks, users=users, contacts=contacts)

# ============================================================================
# DETAIL & UPDATE
# ============================================================================

@audits_bp.route('/<int:id>', methods=['GET'])
@login_required
def view_audit(id):
    audit = ComplianceAudit.query.get_or_404(id)
    users = User.query.filter_by(is_archived=False).all()
    
    # Calculate progress stats
    total_items = audit.audit_items.count()
    compliant_count = audit.audit_items.filter(AuditControlItem.status == 'Compliant').count()
    gap_count = audit.audit_items.filter(AuditControlItem.status == 'Gap').count()
    observation_count = audit.audit_items.filter(AuditControlItem.status == 'Observation').count()
    
    progress = (compliant_count / total_items * 100) if total_items > 0 else 0
    
    return render_template('audits/detail.html', 
                         audit=audit, 
                         progress=round(progress),
                         total_items=total_items,
                         compliant_count=compliant_count,
                         gap_count=gap_count,
                         observation_count=observation_count,
                         users=users)

@audits_bp.route('/<int:id>/header', methods=['POST'])
@login_required
def update_audit_header(id):
    audit = ComplianceAudit.query.get_or_404(id)
    
    audit.status = request.form.get('status', audit.status)
    audit.outcome = request.form.get('outcome') or None
    
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    
    if start_date:
        audit.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        audit.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    db.session.commit()
    flash('Audit details updated.', 'success')
    return redirect(url_for('audits.view_audit', id=id))

@audits_bp.route('/<int:id>/update', methods=['POST'])
@login_required
def update_audit_items(id):
    audit = ComplianceAudit.query.get_or_404(id)
    
    for item in audit.audit_items:
        item_id = str(item.id)
        
        is_applicable = request.form.get(f'item_{item_id}_applicable') == 'on'
        item.is_applicable = is_applicable
        item.justification = request.form.get(f'item_{item_id}_justification')
        item.internal_comments = request.form.get(f'item_{item_id}_internal_comments')
        item.auditor_findings = request.form.get(f'item_{item_id}_auditor_findings')
        
        status = request.form.get(f'item_{item_id}_status')
        if status:
            item.status = status
        
    try:
        db.session.commit()
        flash('Audit updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating audit: {str(e)}', 'danger')
        
    return redirect(url_for('audits.view_audit', id=id))

# ============================================================================
# PARTICIPANTS
# ============================================================================

@audits_bp.route('/<int:id>/participants/add', methods=['POST'])
@login_required
def add_participant(id):
    audit = ComplianceAudit.query.get_or_404(id)
    user_id = request.form.get('user_id')
    
    if user_id:
        user = User.query.get(int(user_id))
        if user and user not in audit.participants:
            audit.participants.append(user)
            db.session.commit()
            flash(f'{user.name} added to the team.', 'success')
    
    return redirect(url_for('audits.view_audit', id=id))

@audits_bp.route('/<int:id>/participants/<int:user_id>/remove', methods=['POST'])
@login_required
def remove_participant(id, user_id):
    audit = ComplianceAudit.query.get_or_404(id)
    user = User.query.get_or_404(user_id)
    
    if user in audit.participants:
        audit.participants.remove(user)
        db.session.commit()
        flash(f'{user.name} removed from the team.', 'success')
    
    return redirect(url_for('audits.view_audit', id=id))

# ============================================================================
# ATTACHMENTS (Global Audit Attachments)
# ============================================================================

@audits_bp.route('/<int:id>/attachments/upload', methods=['POST'])
@login_required
def upload_audit_attachment(id):
    from flask import current_app
    
    audit = ComplianceAudit.query.get_or_404(id)
    
    if 'file' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('audits.view_audit', id=id))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('audits.view_audit', id=id))
    
    original_filename = file.filename
    unique_filename = f"{uuid.uuid4().hex}_{secure_filename(original_filename)}"
    
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file.save(os.path.join(upload_folder, unique_filename))
    
    attachment = Attachment(
        filename=original_filename,
        secure_filename=unique_filename,
        linkable_type='ComplianceAudit',
        linkable_id=audit.id
    )
    db.session.add(attachment)
    db.session.commit()
    
    flash('File uploaded successfully.', 'success')
    return redirect(url_for('audits.view_audit', id=id))

# ============================================================================
# ITEM ATTACHMENTS
# ============================================================================

@audits_bp.route('/<int:id>/item/<int:item_id>/upload', methods=['POST'])
@login_required
def upload_item_attachment(id, item_id):
    from flask import current_app
    
    item = AuditControlItem.query.get_or_404(item_id)
    
    if 'file' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('audits.view_audit', id=id))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('audits.view_audit', id=id))
    
    original_filename = file.filename
    unique_filename = f"{uuid.uuid4().hex}_{secure_filename(original_filename)}"
    
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file.save(os.path.join(upload_folder, unique_filename))
    
    attachment = Attachment(
        filename=original_filename,
        secure_filename=unique_filename,
        linkable_type='AuditControlItem',
        linkable_id=item.id
    )
    db.session.add(attachment)
    db.session.commit()
    
    flash('Evidence uploaded.', 'success')
    return redirect(url_for('audits.view_audit', id=id))

# ============================================================================
# LINKED OBJECTS (Polymorphic Links)
# ============================================================================

@audits_bp.route('/<int:id>/item/<int:item_id>/link', methods=['POST'])
@login_required
def add_item_link(id, item_id):
    item = AuditControlItem.query.get_or_404(item_id)
    
    linkable_type = request.form.get('linkable_type')
    linkable_id = request.form.get('linkable_id')
    description = request.form.get('description')
    
    if linkable_type and linkable_id:
        link = AuditControlLink(
            audit_item_id=item.id,
            linkable_type=linkable_type,
            linkable_id=int(linkable_id),
            description=description
        )
        db.session.add(link)
        db.session.commit()
        flash('Evidence linked.', 'success')
    
    return redirect(url_for('audits.view_audit', id=id))

@audits_bp.route('/<int:id>/item/<int:item_id>/link/<int:link_id>/delete', methods=['POST'])
@login_required
def delete_item_link(id, item_id, link_id):
    link = AuditControlLink.query.get_or_404(link_id)
    db.session.delete(link)
    db.session.commit()
    flash('Link removed.', 'success')
    return redirect(url_for('audits.view_audit', id=id))

# ============================================================================
# EXPORT
# ============================================================================

@audits_bp.route('/<int:id>/export')
@login_required
def export_audit(id):
    audit = ComplianceAudit.query.get_or_404(id)
    
    html = render_template('audits/export_pdf.html', audit=audit, now=datetime.utcnow())
    pdf = HTML(string=html).write_pdf()
    
    return send_file(
        io.BytesIO(pdf),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'defense_pack_{audit.id}.pdf'
    )

@audits_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_audit(id):
    audit = ComplianceAudit.query.get_or_404(id)
    db.session.delete(audit)
    db.session.commit()
    flash('Audit deleted.', 'success')
    return redirect(url_for('audits.list_audits'))
