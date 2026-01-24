from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session
)
from ..models import db, User
from .main import login_required
from functools import wraps
from src.utils.logger import log_audit

# Admin authorization decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            # ... redirect to login
            return redirect(url_for('main.login'))

        user = User.query.get(user_id) # ALWAYS fetch from DB

        if not user or user.role != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('risk.dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function


admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/users')
@login_required
@admin_required
def list_users():
    users = User.query.order_by(User.name).filter_by(is_archived=False).all()
    return render_template('admin/list_users.html', users=users)

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        personal_email = request.form.get('personal_email')

        if User.query.filter_by(email=email).first():
            flash('User with that email already exists.', 'danger')
        else:
            new_user = User(name=name, email=email, role=role, personal_email=personal_email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            
            log_audit(
                event_type='user.created',
                action='create',
                target_object=f"User:{new_user.id}",
                target_info=f"{new_user.name} ({new_user.email})"
            )
            
            flash(f'User "{name}" created successfully.', 'success')
            return redirect(url_for('admin.list_users'))

    return render_template('admin/form_user.html')

@admin_bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    if user.name == 'admin':
        flash('The default admin user cannot be edited.', 'danger')
        return redirect(url_for('admin.list_users'))

    if request.method == 'POST':
        new_email = request.form.get('email')
        
        # Check if email is being changed and if the new one is already taken
        if new_email != user.email and User.query.filter_by(email=new_email).first():
            flash('That email is already in use.', 'danger')
            return render_template('admin/edit_user.html', user=user)

        # Capture old values to detect changes
        old_role = user.role
        
        user.name = request.form.get('name')
        user.email = new_email
        user.personal_email = request.form.get('personal_email')
        user.role = request.form.get('role')
        
        password = request.form.get('password')
        if password:
            user.set_password(password)

        db.session.commit()
        
        # Log Role Change (CRITICAL)
        if old_role != user.role:
            log_audit(
                event_type='user.role_changed',
                action='update',
                target_object=f"User:{user.id}",
                old_role=old_role,
                new_role=user.role
            )
        else:
            log_audit(
                event_type='user.updated',
                action='update',
                target_object=f"User:{user.id}"
            )
            
        flash(f'User "{user.name}" has been updated.', 'success')
        return redirect(url_for('admin.list_users'))

    return render_template('admin/edit_user.html', user=user)


@admin_bp.route('/users/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(id):
    user_to_delete = User.query.get_or_404(id)
    if user_to_delete.name == 'admin':
        flash('The default admin user cannot be deleted.', 'danger')
        return redirect(url_for('admin.list_users'))
        
    user_info = f"{user_to_delete.name} ({user_to_delete.email})"
    db.session.delete(user_to_delete)
    db.session.commit()
    
    log_audit(
        event_type='user.deleted',
        action='delete',
        target_object=f"User:{id}", # Accessing ID after commit/delete typically problematic unless cached, but ID is in arg
        target_info=user_info
    )
    
    flash(f'User "{user_to_delete.name}" has been deleted.', 'success')
    return redirect(url_for('admin.list_users'))


# --- Custom Properties Management ---

from ..models.core import CustomFieldDefinition, CustomFieldValue

@admin_bp.route('/custom-fields')
@login_required
@admin_required
def custom_fields():
    definitions = CustomFieldDefinition.query.order_by(CustomFieldDefinition.entity_type, CustomFieldDefinition.name).all()
    return render_template('admin/custom_fields_list.html', definitions=definitions)

@admin_bp.route('/custom-fields/new', methods=['POST'])
@login_required
@admin_required
def create_custom_field():
    entity_type = request.form.get('entity_type')
    label = request.form.get('label')
    name = request.form.get('name')
    field_type = request.form.get('field_type')
    is_required = request.form.get('is_required') == 'on'
    
    # Basic Validation
    if not all([entity_type, label, name, field_type]):
        flash('All fields are required.', 'danger')
        return redirect(url_for('admin.custom_fields'))
        
    # Check Uniqueness
    existing = CustomFieldDefinition.query.filter_by(entity_type=entity_type, name=name).first()
    if existing:
        flash(f'A field with slug "{name}" already exists for {entity_type}.', 'danger')
        return redirect(url_for('admin.custom_fields'))
        
    new_field = CustomFieldDefinition(
        entity_type=entity_type,
        label=label,
        name=name,
        field_type=field_type,
        is_required=is_required
    )
    
    db.session.add(new_field)
    db.session.commit()
    
    log_audit(
        event_type='custom_field.created',
        action='create',
        target_object=f"CustomFieldDefinition:{new_field.id}",
        target_info=f"{new_field.entity_type}.{new_field.name}"
    )
    
    flash(f'{entity_type} property "{label}" created.', 'success')
    return redirect(url_for('admin.custom_fields'))

@admin_bp.route('/custom-fields/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_custom_field(id):
    field = CustomFieldDefinition.query.get_or_404(id)
    info = f"{field.entity_type}.{field.name}"
    
    # Cascade delete is not set on relationship in core.py properly for values?
    # Actually backref default cascade might not be 'all, delete-orphan'.
    # Manual deletion is safer or we update model. 
    # Let's check model... backref='values'.
    # We should delete values first manually to be sure or verify cascade.
    
    CustomFieldValue.query.filter_by(field_definition_id=id).delete()
    
    db.session.delete(field)
    db.session.commit()
    
    log_audit(
        event_type='custom_field.deleted',
        action='delete',
        target_object=f"CustomFieldDefinition:{id}",
        target_info=info
    )
    
    flash('Custom property deleted.', 'success')
    return redirect(url_for('admin.custom_fields'))
# --- Permissions Matrix ---

from ..models import Module, Group, Permission
from ..services.permissions_service import update_permission_matrix

@admin_bp.route('/permissions', methods=['GET', 'POST'])
@login_required
@admin_required
def permissions_matrix():
    if request.method == 'POST':
        target_type = request.form.get('target_type')
        target_id = request.form.get('target_id', type=int)
        
        # New logic: Look for perm_{target_type}_{target_id}_{module_id} in form
        
        # DEBUG: Log incoming form data
        from flask import current_app
        current_app.logger.info(f"Permissions Update: Target={target_type}, ID={target_id}")
        current_app.logger.info(f"Form Data Keys: {[k for k in request.form.keys() if k.startswith('perm_')]}")

        module_permissions = []
        for key, value in request.form.items():
            # Match only perm_{target_type}_{target_id}_{module_id}
            prefix = f"perm_{target_type}_{target_id}_"
            if key.startswith(prefix):
                try:
                    m_id_str = key[len(prefix):] # Safer than replace in case prefix appears twice
                    m_id = int(m_id_str)
                    
                    current_app.logger.info(f"Found permission: Module {m_id} -> {value}")
                    
                    if value != 'NONE':
                        module_permissions.append({
                            'module_id': m_id,
                            'access_level': value
                        })
                except (ValueError, IndexError) as e:
                    current_app.logger.error(f"Error parsing permission key {key}: {e}")
                    continue
        
        try:
            update_permission_matrix(target_type, target_id, module_permissions)
            flash(f'Permissions updated for {target_type} ID:{target_id}.', 'success')
        except Exception as e:
            flash(f'Error updating permissions: {str(e)}', 'danger')
            
        return redirect(url_for('admin.permissions_matrix', tab=f"{target_type}s"))

    # GET: Fetch data for the matrix
    modules = Module.query.order_by(Module.name).all()
    users = User.query.filter_by(is_archived=False).order_by(User.name).all()
    groups = Group.query.order_by(Group.name).all()
    
    # Pre-fetch existing permission mapping: {user_123: {module_45: 'WRITE'}}
    all_permissions = Permission.query.all()
    matrix = {}
    for p in all_permissions:
        key = f"user_{p.user_id}" if p.user_id else f"group_{p.group_id}"
        if key not in matrix:
            matrix[key] = {}
        matrix[key][p.module_id] = p.access_level.value # "WRITE" or "READ_ONLY"

    active_tab = request.args.get('tab', 'users')
    
    return render_template('admin/permissions_matrix.html', 
                         modules=modules, 
                         users=users, 
                         groups=groups, 
                         matrix=matrix,
                         active_tab=active_tab)
