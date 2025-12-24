from flask import Blueprint, render_template, redirect, url_for, flash, request
from .main import login_required
from ..models.services import BusinessService, ServiceComponent
from ..models.auth import User
from ..extensions import db
from datetime import datetime

services_bp = Blueprint('services', __name__, 
                        template_folder='../templates/services', # Relative to src/routes
                        url_prefix='/services')

@services_bp.route('/')
@login_required
def list_services():
    services = BusinessService.query.all()
    return render_template('services/list.html', services=services)

@services_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create_service():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        owner_id = request.form.get('owner_id')
        criticality = request.form.get('criticality')
        status = request.form.get('status')
        sla_response = request.form.get('sla_response_hours')
        sla_resolution = request.form.get('sla_resolution_hours')
        cost_center = request.form.get('cost_center')
        
        service = BusinessService(
            name=name,
            description=description,
            owner_id=owner_id if owner_id else None,
            criticality=criticality,
            status=status,
            sla_response_hours=int(sla_response) if sla_response else None,
            sla_resolution_hours=int(sla_resolution) if sla_resolution else None,
            cost_center=cost_center
        )
        
        try:
            db.session.add(service)
            db.session.commit()
            flash('Service created successfully!', 'success')
            return redirect(url_for('services.detail', id=service.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating service: {str(e)}', 'danger')
    
    users = User.query.all()
    return render_template('services/form.html', users=users, service=None)

@services_bp.route('/<int:id>')
@login_required
def detail(id):
    service = BusinessService.query.get_or_404(id)
    all_services = BusinessService.query.filter(BusinessService.id != id).all()
    # For polymorphic modal: pass lists of potential components if feasible, 
    # or implement dynamic loading via JS. For MVP, we might just pass types.
    return render_template('services/detail.html', service=service, all_services=all_services)

@services_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_service(id):
    service = BusinessService.query.get_or_404(id)
    
    if request.method == 'POST':
        service.name = request.form.get('name')
        service.description = request.form.get('description')
        service.owner_id = request.form.get('owner_id') if request.form.get('owner_id') else None
        service.criticality = request.form.get('criticality')
        service.status = request.form.get('status')
        
        sla_resp = request.form.get('sla_response_hours')
        service.sla_response_hours = int(sla_resp) if sla_resp else None
        
        sla_res = request.form.get('sla_resolution_hours')
        service.sla_resolution_hours = int(sla_res) if sla_res else None
        
        service.cost_center = request.form.get('cost_center')
        
        try:
            db.session.commit()
            flash('Service updated successfully!', 'success')
            return redirect(url_for('services.detail', id=service.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating service: {str(e)}', 'danger')
            
    users = User.query.all()
    return render_template('services/form.html', users=users, service=service)

@services_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_service(id):
    service = BusinessService.query.get_or_404(id)
    try:
        db.session.delete(service)
        db.session.commit()
        flash('Service deleted successfully.', 'success')
        return redirect(url_for('services.list_services'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting service: {str(e)}', 'danger')
        return redirect(url_for('services.detail', id=id))

@services_bp.route('/<int:id>/dependency/add', methods=['POST'])
@login_required
def add_dependency(id):
    service = BusinessService.query.get_or_404(id)
    target_service_id = request.form.get('target_service_id')
    dependency_type = request.form.get('dependency_type') # 'upstream' (depends on) or 'downstream' (supports)
    
    if not target_service_id:
        flash('Please select a service.', 'warning')
        return redirect(url_for('services.detail', id=id))
        
    target_service = BusinessService.query.get(target_service_id)
    if not target_service:
        flash('Target service not found.', 'danger')
        return redirect(url_for('services.detail', id=id))
        
    if target_service.id == service.id:
        flash('Cannot depend on self.', 'warning')
        return redirect(url_for('services.detail', id=id))
        
    try:
        if dependency_type == 'upstream':
            # Service depends on Target (Service -> Target)
            # upstream_dependencies list should include Target
            if target_service not in service.upstream_dependencies:
                service.upstream_dependencies.append(target_service)
        else:
            # Target depends on Service (Target -> Service)
            # downstream list ... or equivalently, Target's upstream includes Service
            if target_service not in service.downstream_dependencies:
                # Add target to downstream is equivalent to adding service to target's upstream
                # But treating it via the relationship on 'service':
                # 'downstream_dependencies' is a backref. We can append to it? yes dynamic.
                service.downstream_dependencies.append(target_service)
                
        db.session.commit()
        flash('Dependency added.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding dependency: {str(e)}', 'danger')
        
    return redirect(url_for('services.detail', id=id))

@services_bp.route('/<int:id>/dependency/remove/<int:target_id>', methods=['POST'])
@login_required
def remove_dependency(id, target_id):
    service = BusinessService.query.get_or_404(id)
    target_service = BusinessService.query.get_or_404(target_id)
    
    # We don't know if it was upstream or downstream just by ID, so check both or pass type.
    # Assuming the user clicks 'remove' from a specific list.
    dep_type = request.form.get('type') # 'upstream' or 'downstream'
    
    try:
        if dep_type == 'upstream':
            if target_service in service.upstream_dependencies:
                service.upstream_dependencies.remove(target_service)
        elif dep_type == 'downstream':
            if target_service in service.downstream_dependencies:
                service.downstream_dependencies.remove(target_service)
        
        db.session.commit()
        flash('Dependency removed.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing dependency: {str(e)}', 'danger')
        
    return redirect(url_for('services.detail', id=id))

@services_bp.route('/<int:id>/component/add', methods=['POST'])
@login_required
def add_component(id):
    service = BusinessService.query.get_or_404(id)
    comp_type = request.form.get('component_type')
    comp_id = request.form.get('component_id')
    notes = request.form.get('notes')
    
    if not comp_type or not comp_id:
        flash('Invalid component selection.', 'warning')
        return redirect(url_for('services.detail', id=id))
        
    # Create component link
    comp = ServiceComponent(
        service_id=service.id,
        component_type=comp_type,
        component_id=comp_id,
        notes=notes
    )
    
    try:
        db.session.add(comp)
        db.session.commit()
        flash('Component linked successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error linking component: {str(e)}', 'danger')
        
    return redirect(url_for('services.detail', id=id))

@services_bp.route('/component/<int:comp_id>/delete', methods=['POST'])
@login_required
def delete_component(comp_id):
    comp = ServiceComponent.query.get_or_404(comp_id)
    service_id = comp.service_id
    try:
        db.session.delete(comp)
        db.session.commit()
        flash('Component removed.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing component: {str(e)}', 'danger')
    return redirect(url_for('services.detail', id=service_id))
