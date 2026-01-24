from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session
)
from ..models import db, User
from .main import login_required
from functools import wraps
from src.utils.logger import log_audit

from ..services.permissions_service import requires_permission, has_write_permission

# Admin bp
admin_bp = Blueprint('admin', __name__)

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/users')
@login_required
@requires_permission('administration', access_level='READ_ONLY')
def list_users():
    users = User.query.order_by(User.name).filter_by(is_archived=False).all()
    return render_template('admin/list_users.html', users=users)

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@requires_permission('administration', access_level='WRITE')
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
@requires_permission('administration', access_level='WRITE')
def edit_user(id):
    user = User.query.get_or_404(id)
    if user.name == 'admin':
        flash('The default admin user cannot be edited.', 'danger')
        return redirect(url_for('admin.list_users'))

    if request.method == 'POST':
        new_email = request.form.get('email')
        
        if new_email != user.email and User.query.filter_by(email=new_email).first():
            flash('That email is already in use.', 'danger')
            return render_template('admin/edit_user.html', user=user)

        old_role = user.role
        
        user.name = request.form.get('name')
        user.email = new_email
        user.personal_email = request.form.get('personal_email')
        user.role = request.form.get('role')
        
        password = request.form.get('password')
        if password:
            user.set_password(password)

        db.session.commit()
        
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
@requires_permission('administration', access_level='WRITE')
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
        target_object=f"User:{id}", 
        target_info=user_info
    )
    
    flash(f'User "{user_to_delete.name}" has been deleted.', 'success')
    return redirect(url_for('admin.list_users'))


# --- Custom Properties Management ---

from ..models.core import CustomFieldDefinition, CustomFieldValue

@admin_bp.route('/custom-fields')
@login_required
@requires_permission('administration')
def custom_fields():
    definitions = CustomFieldDefinition.query.order_by(CustomFieldDefinition.entity_type, CustomFieldDefinition.name).all()
    return render_template('admin/custom_fields_list.html', definitions=definitions)

@admin_bp.route('/custom-fields/new', methods=['POST'])
@login_required
@requires_permission('administration')
def create_custom_field():
    if not has_write_permission('administration'):
        flash('Write access required to manage custom fields.', 'danger')
        return redirect(url_for('admin.custom_fields'))
    entity_type = request.form.get('entity_type')
    label = request.form.get('label')
    name = request.form.get('name')
    field_type = request.form.get('field_type')
    is_required = request.form.get('is_required') == 'on'
    
    if not all([entity_type, label, name, field_type]):
        flash('All fields are required.', 'danger')
        return redirect(url_for('admin.custom_fields'))
        
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
@requires_permission('administration')
def delete_custom_field(id):
    if not has_write_permission('administration'):
        flash('Write access required to delete custom fields.', 'danger')
        return redirect(url_for('admin.custom_fields'))
    field = CustomFieldDefinition.query.get_or_404(id)
    info = f"{field.entity_type}.{field.name}"
    
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
@requires_permission('administration')
def permissions_matrix():
    if request.method == 'POST':
        if not has_write_permission('administration'):
            flash('Write access required to update permissions.', 'danger')
            return redirect(url_for('admin.permissions_matrix'))
        target_type = request.form.get('target_type')
        target_id = request.form.get('target_id', type=int)
        
        module_permissions = []
        for key, value in request.form.items():
            prefix = f"perm_{target_type}_{target_id}_"
            if key.startswith(prefix):
                try:
                    m_id_str = key[len(prefix):]
                    m_id = int(m_id_str)
                    
                    if value != 'NONE':
                        module_permissions.append({
                            'module_id': m_id,
                            'access_level': value
                        })
                except (ValueError, IndexError):
                    continue
        
        try:
            update_permission_matrix(target_type, target_id, module_permissions)
            flash(f'Permissions updated for {target_type} ID:{target_id}.', 'success')
        except Exception as e:
            flash(f'Error updating permissions: {str(e)}', 'danger')
            
        return redirect(url_for('admin.permissions_matrix', tab=f"{target_type}s"))

    modules = Module.query.order_by(Module.name).all()
    users = User.query.filter_by(is_archived=False).order_by(User.name).all()
    groups = Group.query.order_by(Group.name).all()
    
    all_permissions = Permission.query.all()
    matrix = {}
    for p in all_permissions:
        key = f"user_{p.user_id}" if p.user_id else f"group_{p.group_id}"
        if key not in matrix:
            matrix[key] = {}
        matrix[key][p.module_id] = p.access_level.value 

    active_tab = request.args.get('tab', 'users')
    
    return render_template('admin/permissions_matrix.html', 
                         modules=modules, 
                         users=users, 
                         groups=groups, 
                         matrix=matrix,
                         active_tab=active_tab)
