from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from .main import login_required
from ..extensions import db
from ..models.audits import ComplianceAudit, AuditControlItem
from ..models.security import Framework
from ..models.auth import User
from weasyprint import HTML
import io
from datetime import datetime

audits_bp = Blueprint('audits', __name__, url_prefix='/security/audits')

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
        auditor_id = request.form.get('auditor_id')

        if not name or not framework_id or not auditor_id:
            flash('All fields are required.', 'danger')
            return redirect(url_for('audits.new_audit'))

        try:
            audit = ComplianceAudit.create_snapshot(
                framework_id=int(framework_id),
                name=name,
                auditor_id=int(auditor_id)
            )
            flash('Audit created successfully.', 'success')
            return redirect(url_for('audits.view_audit', id=audit.id))
        except Exception as e:
            flash(f'Error creating audit: {str(e)}', 'danger')
            return redirect(url_for('audits.new_audit'))

    frameworks = Framework.query.filter_by(is_active=True).all()
    users = User.query.filter_by(is_archived=False).all()
    return render_template('audits/new.html', frameworks=frameworks, users=users)

@audits_bp.route('/<int:id>', methods=['GET'])
@login_required
def view_audit(id):
    audit = ComplianceAudit.query.get_or_404(id)
    
    # Calculate progress
    total_items = audit.audit_items.count()
    completed_items = audit.audit_items.filter(AuditControlItem.status != 'Not Started').count()
    progress = (completed_items / total_items * 100) if total_items > 0 else 0
    
    return render_template('audits/detail.html', audit=audit, progress=round(progress))

@audits_bp.route('/<int:id>/update', methods=['POST'])
@login_required
def update_audit_items(id):
    audit = ComplianceAudit.query.get_or_404(id)
    
    # Iterate through form data to update items
    # Form data expected format: 
    # item_{id}_applicable (checkbox)
    # item_{id}_justification (text)
    # item_{id}_status (select)
    # item_{id}_notes (text)
    
    for item in audit.audit_items:
        item_id = str(item.id)
        
        # Update Applicability
        # Checkbox: if present in form, it's True. If not, False.
        is_applicable = request.form.get(f'item_{item_id}_applicable') == 'on'
        item.is_applicable = is_applicable
        
        # Update Justification
        item.justification = request.form.get(f'item_{item_id}_justification')
        
        # Update Status
        status = request.form.get(f'item_{item_id}_status')
        if status:
            item.status = status
            
        # Update Notes
        item.auditor_notes = request.form.get(f'item_{item_id}_notes')
        
    try:
        db.session.commit()
        flash('Audit updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating audit: {str(e)}', 'danger')
        
    return redirect(url_for('audits.view_audit', id=id))

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
        download_name=f'audit_report_{audit.id}.pdf'
    )
