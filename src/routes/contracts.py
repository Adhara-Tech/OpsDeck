from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from datetime import datetime
from ..models import db
from ..models.contracts import Contract, ContractItem
from ..models.procurement import Supplier
from ..models.assets import Asset
from .main import login_required

contracts_bp = Blueprint('contracts', __name__)

@contracts_bp.route('/')
@login_required
def list_contracts():
    status_filter = request.args.get('status')
    
    query = Contract.query
    
    if status_filter:
        if status_filter == 'Expired':
             # Filter by status "Expired" OR dynamically calculated expiry
             query = query.filter((Contract.status == 'Expired') | (Contract.end_date < datetime.today().date()))
        else:
             query = query.filter(Contract.status == status_filter)
    
    contracts = query.order_by(Contract.end_date.asc()).all()
    
    return render_template('contracts/list.html', contracts=contracts, filter=status_filter)

@contracts_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_contract():
    if request.method == 'POST':
        try:
            name = request.form['name']
            contract_type = request.form['contract_type']
            supplier_id = request.form['supplier_id']
            status = request.form['status']
            
            # Dates
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
            
            # Financials
            cost = float(request.form.get('cost', 0))
            currency = request.form.get('currency', 'EUR')
            payment_frequency = request.form.get('payment_frequency')
            
            # Lifecycle
            notice_period_days = int(request.form.get('notice_period_days', 30))
            is_auto_renew = 'is_auto_renew' in request.form
            
            description = request.form.get('description')
            contact_email = request.form.get('contact_email')
            
            contract = Contract(
                name=name,
                contract_type=contract_type,
                supplier_id=supplier_id,
                status=status,
                start_date=start_date,
                end_date=end_date,
                cost=cost,
                currency=currency,
                payment_frequency=payment_frequency,
                notice_period_days=notice_period_days,
                is_auto_renew=is_auto_renew,
                renewal_notes=request.form.get('renewal_notes'),
                description=description,
                contact_email=contact_email
            )
            
            db.session.add(contract)
            db.session.commit()
            
            flash('Contract created successfully.', 'success')
            return redirect(url_for('contracts.contract_detail', id=contract.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating contract: {str(e)}', 'danger')
            
    suppliers = Supplier.query.order_by(Supplier.name).all()
    return render_template('contracts/detail.html', contract=None, suppliers=suppliers)

@contracts_bp.route('/<int:id>', methods=['GET', 'POST'])
@login_required
def contract_detail(id):
    contract = Contract.query.get_or_404(id)
    
    if request.method == 'POST':
        # Handle Edit
        try:
            contract.name = request.form['name']
            contract.contract_type = request.form['contract_type']
            contract.supplier_id = request.form['supplier_id']
            contract.status = request.form['status']
            
            contract.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
            contract.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
            
            contract.cost = float(request.form.get('cost', 0))
            contract.currency = request.form.get('currency', 'EUR')
            contract.payment_frequency = request.form.get('payment_frequency')
            
            contract.notice_period_days = int(request.form.get('notice_period_days', 30))
            contract.is_auto_renew = 'is_auto_renew' in request.form
            contract.renewal_notes = request.form.get('renewal_notes')
            contract.description = request.form.get('description')
            contract.contact_email = request.form.get('contact_email')
            
            db.session.commit()
            flash('Contract updated successfully.', 'success')
            return redirect(url_for('contracts.contract_detail', id=contract.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating contract: {str(e)}', 'danger')

    suppliers = Supplier.query.order_by(Supplier.name).all()
    
    # Pre-fetch linked items for display (could optimize with specific queries if needed)
    linked_items = []
    for item in contract.items:
        obj = item.item
        if obj:
            linked_items.append({
                'id': item.id, # The link ID, for deletion
                'type': item.item_type,
                'name': getattr(obj, 'name', 'Unknown Item'),
                'obj_id': obj.id,
                'url': _get_item_url(item.item_type, obj.id)
            })

    return render_template('contracts/detail.html', 
                           contract=contract, 
                           suppliers=suppliers,
                           linked_items=linked_items)

@contracts_bp.route('/<int:id>/link', methods=['POST'])
@login_required
def link_item(id):
    contract = Contract.query.get_or_404(id)
    item_type = request.form.get('item_type') # 'Asset', 'Subscription', etc.
    item_id = request.form.get('item_id')
    
    if not item_type or not item_id:
        flash('Missing item type or ID.', 'danger')
        return redirect(url_for('contracts.contract_detail', id=id))

    # Verify item exists
    item_class = _get_model_class(item_type)
    if not item_class:
        flash('Invalid item type.', 'danger')
        return redirect(url_for('contracts.contract_detail', id=id))
        
    obj = item_class.query.get(item_id)
    if not obj:
        flash(f'{item_type} with ID {item_id} not found.', 'danger')
        return redirect(url_for('contracts.contract_detail', id=id))

    # Check for existing link
    existing = ContractItem.query.filter_by(
        contract_id=contract.id,
        item_type=item_type,
        item_id=item_id
    ).first()
    
    if existing:
        flash('Item already linked to this contract.', 'info')
    else:
        link = ContractItem(contract_id=contract.id, item_type=item_type, item_id=item_id)
        db.session.add(link)
        db.session.commit()
        flash('Item linked successfully.', 'success')
    
    return redirect(url_for('contracts.contract_detail', id=id))

@contracts_bp.route('/link/<int:link_id>/delete', methods=['POST'])
@login_required
def unlink_item(link_id):
    link = ContractItem.query.get_or_404(link_id)
    contract_id = link.contract_id
    db.session.delete(link)
    db.session.commit()
    flash('Item unlinked.', 'success')
    return redirect(url_for('contracts.contract_detail', id=contract_id))

@contracts_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_contract(id):
    contract = Contract.query.get_or_404(id)
    db.session.delete(contract)
    db.session.commit()
    flash('Contract deleted.', 'success')
    return redirect(url_for('contracts.list_contracts'))

# --- Helpers ---

def _get_model_class(item_type):
    from ..models.assets import Asset, License
    from ..models.procurement import Subscription
    from ..models.services import BusinessService
    
    mapping = {
        'Asset': Asset,
        'Subscription': Subscription,
        'License': License,
        'BusinessService': BusinessService
    }
    return mapping.get(item_type)

def _get_item_url(item_type, item_id):
    if item_type == 'Asset':
        return url_for('assets.asset_detail', id=item_id)
    elif item_type == 'Subscription':
        return url_for('subscriptions.subscription_detail', id=item_id)
    elif item_type == 'License':
        return url_for('licenses.list_licenses') # License detail might be a modal or list
    elif item_type == 'BusinessService':
        return url_for('services.service_detail', service_id=item_id)
    return '#'
