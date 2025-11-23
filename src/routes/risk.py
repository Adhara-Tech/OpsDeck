from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session
)
from ..models import db, Risk, User, Asset
from .main import login_required
from .admin import admin_required
from datetime import datetime

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

@risk_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_risk():
    if request.method == 'POST':
        # Extract form data
        risk = Risk(
            risk_description=request.form['risk_description'],
            owner_id=request.form.get('owner_id'),
            status=request.form.get('status'),
            treatment_strategy=request.form.get('treatment_strategy'),
            
            inherent_impact=int(request.form.get('inherent_impact', 5)),
            inherent_likelihood=int(request.form.get('inherent_likelihood', 5)),
            
            residual_impact=int(request.form.get('residual_impact', 5)),
            residual_likelihood=int(request.form.get('residual_likelihood', 5)),
            
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
                asset = Asset.query.get(asset_id)
                if asset:
                    risk.assets.append(asset)

        db.session.add(risk)
        db.session.commit()
        flash('Risk has been successfully logged.', 'success')
        return redirect(url_for('risk.list_risks'))

    users = User.query.filter_by(is_archived=False).all()
    assets = Asset.query.filter_by(is_archived=False).all()
    return render_template('risk/form.html', users=users, assets=assets)

@risk_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_risk(id):
    risk = Risk.query.get_or_404(id)
    if request.method == 'POST':
        risk.risk_description = request.form['risk_description']
        risk.owner_id = request.form.get('owner_id')
        risk.status = request.form.get('status')
        risk.treatment_strategy = request.form.get('treatment_strategy')
        
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

        # Handle Assets (Clear and Re-add)
        risk.assets = [] # Clear existing
        asset_ids = request.form.getlist('asset_ids')
        if asset_ids:
            for asset_id in asset_ids:
                asset = Asset.query.get(asset_id)
                if asset:
                    risk.assets.append(asset)

        db.session.commit()
        flash('Risk has been updated.', 'success')
        return redirect(url_for('risk.list_risks'))

    users = User.query.filter_by(is_archived=False).all()
    assets = Asset.query.filter_by(is_archived=False).all()
    return render_template('risk/form.html', risk=risk, users=users, assets=assets)