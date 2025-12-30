from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from .main import login_required
from ..models import db, RiskAssessment, RiskAssessmentItem, Risk
from .admin import admin_required
from datetime import datetime
import io

risk_assessment_bp = Blueprint('risk_assessment', __name__, url_prefix='/risk-assessments')

@risk_assessment_bp.route('/')
@login_required
def list_assessments():
    assessments = RiskAssessment.query.order_by(RiskAssessment.created_at.desc()).all()
    return render_template('risk_assessment/list.html', assessments=assessments)

@risk_assessment_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_assessment():
    if request.method == 'POST':
        name = request.form.get('name')
        include_risks = request.form.get('include_risks') == 'yes'
        
        assessment = RiskAssessment(name=name, status='Draft')
        db.session.add(assessment)
        db.session.commit() # Commit to get ID
        
        if include_risks:
            # Snapshot Logic
            open_risks = Risk.query.filter(Risk.status != 'Closed').all()
            for risk in open_risks:
                item = RiskAssessmentItem(
                    assessment_id=assessment.id,
                    original_risk_id=risk.id,
                    risk_description=risk.risk_description,
                    threat_type_name=risk.threat_type.name if risk.threat_type else None,
                    category_list=",".join([c.category for c in risk.categories]),
                    inherent_impact=risk.inherent_impact,
                    inherent_likelihood=risk.inherent_likelihood,
                    residual_impact=risk.residual_impact,
                    residual_likelihood=risk.residual_likelihood,
                    treatment_strategy=risk.treatment_strategy
                )
                db.session.add(item)
            
            assessment.calculate_total_risk()
            db.session.commit()
            flash(f'Assessment created with {len(open_risks)} snapshot items.', 'success')
        else:
            flash('Empty assessment created.', 'success')
            
        return redirect(url_for('risk_assessment.view_assessment', id=assessment.id))
        
    return render_template('risk_assessment/new.html')

@risk_assessment_bp.route('/<int:id>')
@login_required
def view_assessment(id):
    assessment = RiskAssessment.query.get_or_404(id)
    return render_template('risk_assessment/detail.html', assessment=assessment)

@risk_assessment_bp.route('/item/<int:id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_assessment_item(id):
    item = RiskAssessmentItem.query.get_or_404(id)
    if item.assessment.status == 'Locked':
        flash('Cannot edit items in a locked assessment.', 'warning')
        return redirect(url_for('risk_assessment.view_assessment', id=item.assessment_id))
        
    item.risk_description = request.form.get('risk_description')
    item.residual_impact = int(request.form.get('residual_impact'))
    item.residual_likelihood = int(request.form.get('residual_likelihood'))
    item.mitigation_notes = request.form.get('mitigation_notes')
    
    # Recalculate total risk for the assessment
    item.assessment.calculate_total_risk()
    
    db.session.commit()
    flash('Assessment item updated.', 'success')
    return redirect(url_for('risk_assessment.view_assessment', id=item.assessment_id))

@risk_assessment_bp.route('/<int:id>/lock', methods=['POST'])
@login_required
@admin_required
def lock_assessment(id):
    assessment = RiskAssessment.query.get_or_404(id)
    
    # Checkbox from the sync modal
    sync_to_live = request.form.get('sync_to_live') == 'on'
    
    # 1. Lock the assessment
    assessment.status = 'Locked'
    assessment.locked_at = datetime.utcnow()
    assessment.calculate_total_risk()
    
    # 2. Write-back: Update live risks if requested
    updated_count = 0
    if sync_to_live:
        for item in assessment.items:
            # Only update if there's a linked original risk
            if item.original_risk_id:
                live_risk = Risk.query.get(item.original_risk_id)
                if live_risk:
                    # Update residual scores from assessment
                    live_risk.residual_impact = item.residual_impact
                    live_risk.residual_likelihood = item.residual_likelihood
                    
                    # Conditional status update based on residual score
                    if item.residual_score < 5:
                        live_risk.status = 'Mitigated'
                    elif item.residual_score >= 15:
                        live_risk.status = 'In Treatment'
                    
                    updated_count += 1
    
    db.session.commit()
    
    msg = 'Assessment locked successfully.'
    if updated_count > 0:
        msg += f' {updated_count} live risk(s) updated with new scores.'
    flash(msg, 'success')
    return redirect(url_for('risk_assessment.view_assessment', id=assessment.id))

@risk_assessment_bp.route('/<int:id>/pdf')
@login_required
def export_pdf(id):
    assessment = RiskAssessment.query.get_or_404(id)
    from weasyprint import HTML
    
    html = render_template('risk_assessment/pdf_report.html', assessment=assessment, now=datetime.utcnow())
    pdf = HTML(string=html).write_pdf()
    
    return send_file(
        io.BytesIO(pdf),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'Assessment_{assessment.name.replace(" ", "_")}.pdf'
    )
