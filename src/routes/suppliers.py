from flask import (
    Blueprint, render_template, request, redirect, url_for, flash
)
from ..models import db, Supplier
from .main import login_required
from ..services.permissions_service import requires_permission

suppliers_bp = Blueprint('suppliers', __name__)

@suppliers_bp.route('/')
@login_required
@requires_permission('business_ops', access_level='READ_ONLY')
def suppliers():
    suppliers = Supplier.query.filter_by(is_archived=False).all()
    return render_template('suppliers/list.html', suppliers=suppliers)

@suppliers_bp.route('/archived')
@login_required
@requires_permission('business_ops', access_level='READ_ONLY')
def archived_suppliers():
    suppliers = Supplier.query.filter_by(is_archived=True).all()
    return render_template('suppliers/archived.html', suppliers=suppliers)

@suppliers_bp.route('/<int:id>/archive', methods=['POST'])
@login_required
@requires_permission('business_ops', access_level='WRITE')
def archive_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    supplier.is_archived = True
    db.session.commit()
    flash(f'Supplier "{supplier.name}" has been archived.')
    return redirect(url_for('suppliers.suppliers'))


@suppliers_bp.route('/<int:id>/unarchive', methods=['POST'])
@login_required
@requires_permission('business_ops', access_level='WRITE')
def unarchive_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    supplier.is_archived = False
    db.session.commit()
    flash(f'Supplier "{supplier.name}" has been restored.')
    return redirect(url_for('suppliers.archived_suppliers'))

@suppliers_bp.route('/new', methods=['GET', 'POST'])
@login_required
@requires_permission('business_ops', access_level='READ_ONLY')
def new_supplier():
    if request.method == 'POST':
        # Manual check for WRITE access
        from ..services.permissions_cache import permissions_cache
        from flask import session
        user_id = session.get('user_id')
        user_role = session.get('user_role')
        if (user_role or session.get('role')) != 'admin':
            perms = permissions_cache.get(user_id)
            if perms.get('business_ops') != 'WRITE':
                flash('Write access required for this action.', 'danger')
                return redirect(url_for('suppliers.suppliers'))
        supplier = Supplier(
            name=request.form['name'],
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            compliance_status=request.form.get('compliance_status'),
            gdpr_dpa_signed=datetime.strptime(request.form['gdpr_dpa_signed'], '%Y-%m-%d').date() if request.form.get('gdpr_dpa_signed') else None,
            security_assessment_completed=datetime.strptime(request.form['security_assessment_completed'], '%Y-%m-%d').date() if request.form.get('security_assessment_completed') else None,
            compliance_notes=request.form.get('compliance_notes')
        )
        db.session.add(supplier)
        db.session.commit()
        flash('Supplier created successfully!')
        return redirect(url_for('suppliers.suppliers'))

    return render_template('suppliers/form.html')

@suppliers_bp.route('/<int:id>')
@login_required
@requires_permission('business_ops', access_level='READ_ONLY')
def supplier_detail(id):
    supplier = Supplier.query.get_or_404(id)
    return render_template('suppliers/detail.html', supplier=supplier)

@suppliers_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@requires_permission('business_ops', access_level='READ_ONLY')
def edit_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    
    if request.method == 'POST':
        # Manual check for WRITE access
        from ..services.permissions_cache import permissions_cache
        from flask import session
        user_id = session.get('user_id')
        user_role = session.get('user_role')
        if (user_role or session.get('role')) != 'admin':
            perms = permissions_cache.get(user_id)
            if perms.get('business_ops') != 'WRITE':
                flash('Write access required for this action.', 'danger')
                return redirect(url_for('suppliers.supplier_detail', id=id))
        supplier.name = request.form['name']
        supplier.email = request.form.get('email')
        supplier.phone = request.form.get('phone')
        supplier.address = request.form.get('address')
        supplier.compliance_status = request.form.get('compliance_status')
        supplier.gdpr_dpa_signed = datetime.strptime(request.form['gdpr_dpa_signed'], '%Y-%m-%d').date() if request.form.get('gdpr_dpa_signed') else None
        # This line was already here, but now it's just part of the updates
        supplier.security_assessment_completed = datetime.strptime(request.form['security_assessment_completed'], '%Y-%m-%d').date() if request.form.get('security_assessment_completed') else None
        supplier.compliance_notes = request.form.get('compliance_notes')
        supplier.data_storage_region = request.form.get('data_storage_region') # <-- ADD THIS LINE
        db.session.commit()
        flash('Supplier updated successfully!')
        return redirect(url_for('suppliers.supplier_detail', id=supplier.id)) # Redirect to detail view
    
    return render_template('suppliers/form.html', supplier=supplier)

@suppliers_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@requires_permission('business_ops', access_level='WRITE')
def delete_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    db.session.delete(supplier)
    db.session.commit()
    flash('Supplier deleted successfully!')
    return redirect(url_for('suppliers.suppliers'))