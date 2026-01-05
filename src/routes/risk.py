from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
)
from ..models import db, Risk, User, Asset, RiskCategory, RISK_CATEGORIES, RISK_CATEGORY_COLORS, RiskAffectedItem, RiskAssessment, ThreatType

from ..models.security import RiskReference
from ..models.activities import SecurityActivity
from ..models.auth import Group
from ..models.procurement import Subscription
from ..models.policy import Policy
from ..models.core import Documentation, Link
from .main import login_required
from .admin import admin_required
from datetime import datetime

risk_bp = Blueprint('risk', __name__)

@risk_bp.route('/dashboard')
@login_required
def dashboard():
    # 1. KPIs
    all_risks = Risk.query.all()
    total_risks = len(all_risks)
    
    critical_risks_count = sum(1 for r in all_risks if r.residual_score >= 20)
    risk_exposure = sum(r.residual_score for r in all_risks)
    
    # 2. Risk Matrix Data
    # Group risks by (impact, likelihood)
    matrix = {}
    for r in all_risks:
        key = (r.residual_impact, r.residual_likelihood)
        if key not in matrix:
            matrix[key] = []
        matrix[key].append(r)
        
    # 3. Historical Burn-down Data
    assessments = RiskAssessment.query.filter(RiskAssessment.total_residual_risk.isnot(None)).order_by(RiskAssessment.created_at).all()
    
    burn_down_labels = [a.created_at.strftime('%b %Y') for a in assessments]
    burn_down_data = [a.total_residual_risk for a in assessments]
    
    # Add Current State
    burn_down_labels.append('Current')
    burn_down_data.append(risk_exposure)
    
    # 4. Threat Type Distribution
    threat_counts = {}
    for r in all_risks:
        cat = r.threat_type.category if r.threat_type else 'Uncategorized'
        threat_counts[cat] = threat_counts.get(cat, 0) + 1
        
    threat_labels = list(threat_counts.keys())
    threat_data = list(threat_counts.values())

    return render_template('risk/dashboard.html', 
                           total_risks=total_risks,
                           critical_risks_count=critical_risks_count,
                           risk_exposure=risk_exposure,
                           matrix=matrix,
                           burn_down_labels=burn_down_labels,
                           burn_down_data=burn_down_data,
                           threat_labels=threat_labels,
                           threat_data=threat_data)
from .main import login_required

risk_bp = Blueprint('risk', __name__)

@risk_bp.route('/')
@login_required
def list_risks():
    query = Risk.query

    # Filters
    status = request.args.get('status')
    if status:
        query = query.filter(Risk.status == status)

    strategy = request.args.get('strategy')
    if strategy:
        query = query.filter(Risk.treatment_strategy == strategy)

    owner_id = request.args.get('owner_id')
    if owner_id:
        query = query.filter(Risk.owner_id == owner_id)

    residual_impact = request.args.get('residual_impact', type=int)
    if residual_impact:
        query = query.filter(Risk.residual_impact == residual_impact)

    residual_likelihood = request.args.get('residual_likelihood', type=int)
    if residual_likelihood:
        query = query.filter(Risk.residual_likelihood == residual_likelihood)   

    min_score = request.args.get('min_score', type=int)
    if min_score:
        query = query.filter((Risk.residual_impact * Risk.residual_likelihood) >= min_score)

    risks = query.order_by((Risk.residual_impact * Risk.residual_likelihood).desc(), Risk.created_at.desc()).all()
    
    return render_template('risk/list.html', risks=risks)

@risk_bp.route('/dashboard')
@login_required
def dashboard():
    # 1. KPIs
    all_risks = Risk.query.all()
    total_risks = len(all_risks)
    
    critical_risks_count = sum(1 for r in all_risks if r.residual_score >= 20)
    risk_exposure = sum(r.residual_score for r in all_risks)
    
    # Efficiency (avoid division by zero)
    total_reduction = sum(r.risk_reduction_percentage for r in all_risks)
    avg_efficiency = round(total_reduction / total_risks, 1) if total_risks > 0 else 0.0

    # 2. Charts Data
    
    # Strategy Distribution
    strategies = {}
    for r in all_risks:
        s = r.treatment_strategy or 'Undefined'
        strategies[s] = strategies.get(s, 0) + 1
    
    strategy_labels = list(strategies.keys())
    strategy_data = list(strategies.values())

    # --- TOP OWNERS (UPDATED for Clickability) ---
    # Group by (id, name) to preserve the ID for linking
    owners_map = {} 
    for r in all_risks:
        if r.owner:
            key = (r.owner.id, r.owner.name)
        else:
            key = (None, 'Unassigned')
        
        owners_map[key] = owners_map.get(key, 0) + 1
    
    # Sort by count desc and take top 5
    sorted_owners = sorted(owners_map.items(), key=lambda item: item[1], reverse=True)[:5]
    
    # Unpack into separate lists (names for labels, ids for links, counts for data)
    owner_labels = [item[0][1] for item in sorted_owners]
    owner_ids = [item[0][0] for item in sorted_owners]
    owner_data = [item[1] for item in sorted_owners]
    # ---------------------------------------------

    # Heatmap Data (Scatter Plot format: x=Likelihood, y=Impact)
    heatmap_map = {}
    
    for r in all_risks:
        x = r.residual_likelihood or 1
        y = r.residual_impact or 1
        coord = (x, y)
        
        if coord not in heatmap_map:
            heatmap_map[coord] = {'count': 0, 'titles': []}
        
        heatmap_map[coord]['count'] += 1
        heatmap_map[coord]['titles'].append(r.risk_description)

    heatmap_data = []
    for (x, y), data in heatmap_map.items():
        tooltip_text = f"{data['count']} Risks:\n" + "\n".join([f"- {t}" for t in data['titles'][:5]])
        if len(data['titles']) > 5:
            tooltip_text += f"\n...and {len(data['titles']) - 5} more"

        heatmap_data.append({
            'x': x,
            'y': y,
            'r': data['count'],
            'title': tooltip_text
        })

    # 3. Tables
    top_critical_risks = sorted(
        [r for r in all_risks if r.residual_score >= 15],
        key=lambda x: x.residual_score,
        reverse=True
    )[:5]

    accepted_risks = [r for r in all_risks if r.treatment_strategy == 'Accept']

    return render_template('risk/dashboard.html',
                           total_risks=total_risks,
                           critical_risks_count=critical_risks_count,
                           risk_exposure=risk_exposure,
                           avg_efficiency=avg_efficiency,
                           strategy_labels=strategy_labels,
                           strategy_data=strategy_data,
                           owner_labels=owner_labels,
                           owner_ids=owner_ids,  # <-- PASSING THIS NEW VARIABLE
                           owner_data=owner_data,
                           heatmap_data=heatmap_data,
                           top_critical_risks=top_critical_risks,
                           accepted_risks=accepted_risks)

@risk_bp.route('/dashboard/pdf')
@login_required
def dashboard_pdf():
    from weasyprint import HTML
    from flask import make_response
    
    # Re-fetch data for PDF (similar to dashboard but optimized for print)
    all_risks = Risk.query.all()
    total_risks = len(all_risks)
    
    # 1. KPIs
    critical_risks_count = sum(1 for r in all_risks if r.residual_score >= 20)
    risk_exposure = sum(r.residual_score for r in all_risks)
    
    total_reduction = sum(r.risk_reduction_percentage for r in all_risks)
    avg_efficiency = round(total_reduction / total_risks, 1) if total_risks > 0 else 0.0

    # 2. Charts Data
    # Strategy Data for PDF (Dictionary for loop)
    strategies = {}
    for r in all_risks:
        s = r.treatment_strategy or 'Undefined'
        strategies[s] = strategies.get(s, 0) + 1

    # Heatmap Counts for Grid (x, y) -> count
    heatmap_counts = {}
    for r in all_risks:
        coord = (r.residual_likelihood, r.residual_impact)
        heatmap_counts[coord] = heatmap_counts.get(coord, 0) + 1

    # 3. Lists for Page 1
    # Top Critical Risks (Top 10 for PDF summary)
    top_critical_risks = sorted(
        [r for r in all_risks if r.residual_score >= 15],
        key=lambda x: x.residual_score,
        reverse=True
    )[:10]

    accepted_risks = [r for r in all_risks if r.treatment_strategy == 'Accept']

    # 4. Detailed List for Page 2 (Full Register)
    # Sort by Criticality (Residual Score) Descending
    detailed_risks = sorted(
        all_risks,
        key=lambda x: x.residual_score,
        reverse=True
    )

    # 5. Metadata
    user = User.query.get(session.get('user_id'))

    # Render HTML
    html_content = render_template(
        'risk/dashboard_pdf.html',
        total_risks=total_risks,
        critical_risks_count=critical_risks_count,
        risk_exposure=risk_exposure,
        avg_efficiency=avg_efficiency,
        strategies=strategies,
        heatmap_counts=heatmap_counts,
        top_critical_risks=top_critical_risks,
        accepted_risks=accepted_risks,
        detailed_risks=detailed_risks,
        generated_at=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        generated_by=user.name if user else 'System'
    )
    
    # Generate PDF
    pdf_file = HTML(string=html_content).write_pdf()
    
    response = make_response(pdf_file)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=risk_report.pdf'
    
    return response

@risk_bp.route('/<int:id>')
@login_required
def detail(id):
    risk = Risk.query.get_or_404(id)
    return render_template('risk/detail.html', risk=risk)

from ..models.security import ThreatType

@risk_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_risk():
    if request.method == 'POST':
        # Extract form data
        threat_type_id = request.form.get('threat_type_id')
        
        risk = Risk(
            risk_description=request.form['risk_description'],
            extended_description=request.form.get('extended_description'),
            owner_id=request.form.get('owner_id'),
            status=request.form.get('status', 'Draft'),
            treatment_strategy=request.form.get('treatment_strategy'),
            threat_type_id=int(threat_type_id) if threat_type_id else None,
            
            inherent_impact=int(request.form.get('inherent_impact', 5)),
            inherent_likelihood=int(request.form.get('inherent_likelihood', 5)),
            
            # INTEGRITY RULE: Residual = Inherent on creation
            # Residual values can only be modified via Risk Assessments
            residual_impact=int(request.form.get('inherent_impact', 5)),
            residual_likelihood=int(request.form.get('inherent_likelihood', 5)),
            
            mitigation_plan=request.form.get('mitigation_plan'),
            link=request.form.get('link')
        )
        
        # Handle date
        review_date = request.form.get('next_review_date')
        if review_date:
            risk.next_review_date = datetime.strptime(review_date, '%Y-%m-%d').date()
            
        # Handle Assets
        asset_ids = request.form.getlist('asset_ids')
        if asset_ids:
            for asset_id in asset_ids:
                # Verify asset exists
                if Asset.query.get(asset_id):
                    item = RiskAffectedItem(linkable_type='Asset', linkable_id=asset_id)
                    risk.affected_items.append(item)
        
        # Handle Categories
        db.session.add(risk)
        db.session.flush()  # Get the risk.id
        category_names = request.form.getlist('category_ids')
        for cat_name in category_names:
            if cat_name in RISK_CATEGORIES:
                risk_cat = RiskCategory(risk_id=risk.id, category=cat_name)
                db.session.add(risk_cat)
        
        # Handle Mitigation Activities
        activity_ids = request.form.getlist('mitigation_activity_ids')
        for activity_id in activity_ids:
            activity = SecurityActivity.query.get(activity_id)
            if activity:
                risk.mitigation_activities.append(activity)

        db.session.commit()
        flash('Risk has been successfully logged.', 'success')
        return redirect(url_for('risk.list_risks'))

    users = User.query.filter_by(is_archived=False).all()
    activities = SecurityActivity.query.order_by(SecurityActivity.name).all()
    threat_types = ThreatType.query.order_by(ThreatType.category, ThreatType.name).all()
    
    return render_template('risk/form.html', users=users, activities=activities,
                           risk_categories=RISK_CATEGORIES, category_colors=RISK_CATEGORY_COLORS,
                           threat_types=threat_types)

from src.utils.logger import log_audit

@risk_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_risk(id):
    risk = Risk.query.get_or_404(id)
    if request.method == 'POST':
        # Capture old values for audit
        old_score = risk.residual_score
        
        risk.risk_description = request.form['risk_description']
        risk.extended_description = request.form.get('extended_description')
        risk.owner_id = request.form.get('owner_id')
        risk.status = request.form.get('status')
        risk.treatment_strategy = request.form.get('treatment_strategy')
        
        threat_type_id = request.form.get('threat_type_id')
        risk.threat_type_id = int(threat_type_id) if threat_type_id else None
        
        risk.inherent_impact = int(request.form.get('inherent_impact', 5))
        risk.inherent_likelihood = int(request.form.get('inherent_likelihood', 5))
        
        risk.residual_impact = int(request.form.get('residual_impact', 5))
        risk.residual_likelihood = int(request.form.get('residual_likelihood', 5))
        
        risk.mitigation_plan = request.form.get('mitigation_plan')
        risk.link = request.form.get('link')
        
        # Handle date
        review_date = request.form.get('next_review_date')
        if review_date:
            risk.next_review_date = datetime.strptime(review_date, '%Y-%m-%d').date()
        else:
            risk.next_review_date = None

        # Handle Categories (Clear and Re-add)
        RiskCategory.query.filter_by(risk_id=risk.id).delete()
        category_names = request.form.getlist('category_ids')
        for cat_name in category_names:
            if cat_name in RISK_CATEGORIES:
                risk_cat = RiskCategory(risk_id=risk.id, category=cat_name)
                db.session.add(risk_cat)
        
        # Handle Mitigation Activities (Clear and Re-add)
        risk.mitigation_activities = []
        activity_ids = request.form.getlist('mitigation_activity_ids')
        for activity_id in activity_ids:
            activity = SecurityActivity.query.get(activity_id)
            if activity:
                risk.mitigation_activities.append(activity)

        db.session.commit()
        
        log_audit(
            event_type='risk.updated',
            action='update',
            target_object=f"Risk:{risk.id}",
            old_residual_score=old_score,
            new_residual_score=risk.residual_score
        )
        
        flash('Risk has been updated.', 'success')
        return redirect(url_for('risk.detail', id=risk.id))

    users = User.query.filter_by(is_archived=False).all()
    activities = SecurityActivity.query.order_by(SecurityActivity.name).all()
    threat_types = ThreatType.query.order_by(ThreatType.category, ThreatType.name).all()
    
    return render_template('risk/form.html', risk=risk, users=users, activities=activities,
                           risk_categories=RISK_CATEGORIES, category_colors=RISK_CATEGORY_COLORS,
                           threat_types=threat_types)

@risk_bp.route('/<int:id>/affected_items/add', methods=['POST'])
@login_required
@admin_required
def add_affected_item(id):
    risk = Risk.query.get_or_404(id)
    linkable_type = request.form.get('linkable_type')
    linkable_id = request.form.get('linkable_id')
    
    if not linkable_type or not linkable_id:
        flash('Invalid item selected.', 'danger')
        return redirect(url_for('risk.detail', id=id))

    # Check if already exists
    exists = RiskAffectedItem.query.filter_by(
        risk_id=risk.id,
        linkable_type=linkable_type,
        linkable_id=linkable_id
    ).first()
    
    if exists:
        flash('Item is already linked to this risk.', 'warning')
        return redirect(url_for('risk.detail', id=id))
        
    # Verify existence of the target object
    model_map = {
        'User': User,
        'Group': Group,
        'Asset': Asset,
        'Subscription': Subscription
    }
    
    model = model_map.get(linkable_type)
    if not model:
        flash(f'Unsupported item type: {linkable_type}', 'danger')
        return redirect(url_for('risk.detail', id=id))
        
    target = model.query.get(linkable_id)
    if not target:
        flash('Target item not found.', 'danger')
        return redirect(url_for('risk.detail', id=id))
        
    item = RiskAffectedItem(risk_id=risk.id, linkable_type=linkable_type, linkable_id=linkable_id)
    db.session.add(item)
    db.session.commit()
    
    flash('Affected item added successfully.', 'success')
    return redirect(url_for('risk.detail', id=id))

@risk_bp.route('/affected_items/<int:item_id>/delete', methods=['POST'])
@login_required
@admin_required
def remove_affected_item(item_id):
    item = RiskAffectedItem.query.get_or_404(item_id)
    risk_id = item.risk_id
    db.session.delete(item)
    db.session.commit()
    flash('Affected item removed.', 'success')
    return redirect(url_for('risk.detail', id=risk_id))

@risk_bp.route('/api/items/<item_type>')
@login_required
def api_get_items(item_type):
    """API endpoint to fetch items by type for dynamic selector."""
    model_map = {
        'User': User,
        'Group': Group,
        'Asset': Asset,
        'Subscription': Subscription
    }
    
    model = model_map.get(item_type)
    if not model:
        return jsonify([])
    
    items = []
    if item_type == 'User':
        records = model.query.filter_by(is_archived=False).order_by(model.name).all()
        items = [{'id': r.id, 'name': r.name, 'detail': r.email} for r in records]
    elif item_type == 'Group':
        records = model.query.order_by(model.name).all()
        items = [{'id': r.id, 'name': r.name, 'detail': f'{len(r.users)} members'} for r in records]
    elif item_type == 'Asset':
        records = model.query.filter_by(is_archived=False).order_by(model.name).all()
        items = [{'id': r.id, 'name': r.name, 'detail': r.serial_number or r.status} for r in records]
    elif item_type == 'Subscription':
        records = model.query.filter_by(is_archived=False).order_by(model.name).all()
        items = [{'id': r.id, 'name': r.name, 'detail': r.supplier.name if r.supplier else 'N/A'} for r in records]
    
    return jsonify(items)


@risk_bp.route('/api/references/<ref_type>')
@login_required
def api_get_references(ref_type):
    """API endpoint to fetch reference items by type for dynamic selector."""
    model_map = {
        'Policy': Policy,
        'Documentation': Documentation,
        'Link': Link
    }
    
    model = model_map.get(ref_type)
    if not model:
        return jsonify([])
    
    items = []
    if ref_type == 'Policy':
        records = model.query.order_by(model.title).all()
        items = [{'id': r.id, 'name': r.title, 'detail': r.category or 'General'} for r in records]
    elif ref_type == 'Documentation':
        records = model.query.order_by(model.name).all()
        items = [{'id': r.id, 'name': r.name, 'detail': r.description[:50] + '...' if r.description and len(r.description) > 50 else (r.description or 'No description')} for r in records]
    elif ref_type == 'Link':
        records = model.query.order_by(model.name).all()
        items = [{'id': r.id, 'name': r.name, 'detail': r.url[:40] + '...' if len(r.url) > 40 else r.url} for r in records]
    
    return jsonify(items)


@risk_bp.route('/<int:id>/references/add', methods=['POST'])
@login_required
@admin_required
def add_reference(id):
    """Add a reference (Policy, Documentation, Link) to a risk."""
    risk = Risk.query.get_or_404(id)
    linkable_type = request.form.get('linkable_type')
    linkable_id = request.form.get('linkable_id')
    
    if not linkable_type or not linkable_id:
        flash('Invalid reference selected.', 'danger')
        return redirect(url_for('risk.detail', id=id))

    # Check if already exists
    exists = RiskReference.query.filter_by(
        risk_id=risk.id,
        linkable_type=linkable_type,
        linkable_id=linkable_id
    ).first()
    
    if exists:
        flash('Reference is already linked to this risk.', 'warning')
        return redirect(url_for('risk.detail', id=id))
        
    # Verify existence of the target object
    model_map = {
        'Policy': Policy,
        'Documentation': Documentation,
        'Link': Link
    }
    
    model = model_map.get(linkable_type)
    if not model:
        flash(f'Unsupported reference type: {linkable_type}', 'danger')
        return redirect(url_for('risk.detail', id=id))
        
    target = model.query.get(linkable_id)
    if not target:
        flash('Target reference not found.', 'danger')
        return redirect(url_for('risk.detail', id=id))
        
    ref = RiskReference(risk_id=risk.id, linkable_type=linkable_type, linkable_id=linkable_id)
    db.session.add(ref)
    db.session.commit()
    
    flash('Reference added successfully.', 'success')
    return redirect(url_for('risk.detail', id=id))


@risk_bp.route('/references/<int:ref_id>/delete', methods=['POST'])
@login_required
@admin_required
def remove_reference(ref_id):
    """Remove a reference from a risk."""
    ref = RiskReference.query.get_or_404(ref_id)
    risk_id = ref.risk_id
    db.session.delete(ref)
    db.session.commit()
    flash('Reference removed.', 'success')
    return redirect(url_for('risk.detail', id=risk_id))