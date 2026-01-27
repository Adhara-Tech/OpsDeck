import os
import uuid
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app
)
from ..models import db, User, Attachment, OrgChartSnapshot
from ..models.core import CustomFieldDefinition

from .main import login_required
from weasyprint import HTML
from ..services.permissions_service import requires_permission

users_bp = Blueprint('users', __name__)

@users_bp.route('/')
@login_required
@requires_permission('administration', access_level='READ_ONLY')
def users():
    users = User.query.filter_by(is_archived=False).order_by(User.name).all()
    return render_template('users/list.html', users=users)

@users_bp.route('/org-chart')
@login_required
@requires_permission('administration', access_level='READ_ONLY')
def org_chart():
    users = User.query.filter_by(is_archived=False, hide_from_org_chart=False).all()
    return render_template('users/org_chart.html', users=users)

@users_bp.route('/archived')
@login_required
@requires_permission('administration', access_level='READ_ONLY')
def archived_users():
    users = User.query.filter_by(is_archived=True).all()
    return render_template('users/archived.html', users=users)


@users_bp.route('/<int:id>/archive', methods=['POST'])
@login_required
@requires_permission('administration', access_level='WRITE')
def archive_user(id):
    user = User.query.get_or_404(id)
    user.is_archived = True
    db.session.commit()
    flash(f'User "{user.name}" has been archived.')
    return redirect(url_for('users.users'))


@users_bp.route('/<int:id>/unarchive', methods=['POST'])
@login_required
@requires_permission('administration', access_level='WRITE')
def unarchive_user(id):
    user = User.query.get_or_404(id)
    user.is_archived = False
    db.session.commit()
    flash(f'User "{user.name}" has been restored.')
    return redirect(url_for('users.archived_users'))

@users_bp.route('/<int:id>')
@login_required
@requires_permission('administration', access_level='READ_ONLY')
def user_detail(id):
    user = User.query.get_or_404(id)
    custom_field_definitions = CustomFieldDefinition.query.filter_by(entity_type='User').all()
    return render_template('users/detail.html', user=user, custom_field_definitions=custom_field_definitions)

@users_bp.route('/new', methods=['GET', 'POST'])
@login_required
@requires_permission('administration', access_level='READ_ONLY')
def new_user():
    users = User.query.filter_by(is_archived=False).order_by(User.name).all()
    custom_field_definitions = CustomFieldDefinition.query.filter_by(entity_type='User').all()

    if request.method == 'POST':
        # Manual check for WRITE access
        from ..services.permissions_cache import permissions_cache
        from flask import session
        user_id = session.get('user_id')
        user_role = session.get('user_role')
        if user_role != 'admin':
            perms = permissions_cache.get(user_id)
            if perms.get('administration') != 'WRITE':
                flash('Write access required for this action.', 'danger')
                return redirect(url_for('users.users'))
        manager_id = request.form.get('manager_id')
        buddy_id = request.form.get('buddy_id')

        user = User(
            name=request.form['name'],
            email=request.form.get('email'),
            department=request.form.get('department'),
            job_title=request.form.get('job_title'),
            manager_id=int(manager_id) if manager_id else None,
            buddy_id=int(buddy_id) if buddy_id else None
        )
        db.session.add(user)
        db.session.commit()
        
        # Save custom properties after user has ID
        user.save_custom_properties(request.form)
        db.session.commit()
        
        flash('User created successfully!')
        return redirect(url_for('users.users'))

    return render_template('users/form.html', users=users, custom_field_definitions=custom_field_definitions)

@users_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@requires_permission('administration', access_level='READ_ONLY')
def edit_user(id):
    user = User.query.get_or_404(id)

    users = User.query.filter_by(is_archived=False).order_by(User.name).all()
    custom_field_definitions = CustomFieldDefinition.query.filter_by(entity_type='User').all()

    if request.method == 'POST':
        # Manual check for WRITE access
        from ..services.permissions_cache import permissions_cache
        from flask import session
        user_id = session.get('user_id')
        user_role = session.get('user_role')
        if user_role != 'admin':
            perms = permissions_cache.get(user_id)
            if perms.get('administration') != 'WRITE':
                flash('Write access required for this action.', 'danger')
                return redirect(url_for('users.user_detail', id=id))
        user.name = request.form['name']
        user.email = request.form.get('email')
        user.department = request.form.get('department')
        user.job_title = request.form.get('job_title')
        
        manager_id = request.form.get('manager_id')
        user.manager_id = int(manager_id) if manager_id else None
        
        buddy_id = request.form.get('buddy_id')
        user.buddy_id = int(buddy_id) if buddy_id else None
        
        # Handle org chart visibility toggle
        user.hide_from_org_chart = request.form.get('hide_from_org_chart') == 'on'
        
        user.save_custom_properties(request.form)
        
        db.session.commit()
        flash('User updated successfully!')
        return redirect(url_for('users.users'))

    return render_template('users/form.html', user=user, users=users, custom_field_definitions=custom_field_definitions)


@users_bp.route('/<int:id>/inventory/generate', methods=['POST'])
@login_required
@requires_permission('administration', access_level='WRITE')
def generate_inventory(id):
    """
    Genera un snapshot en PDF del inventario del usuario y lo guarda
    como un adjunto enlazado a ese usuario.
    """
    user = User.query.get_or_404(id)
    
    # 1. Renderizar la plantilla HTML específica para el PDF
    html_content = render_template(
        'users/inventory_pdf.html', 
        user=user,
        generated_at=datetime.now()
    )
    
    # 2. Generar los bytes del PDF en memoria
    try:
        pdf_bytes = HTML(string=html_content).write_pdf()
    except Exception as e:
        current_app.logger.error(f"Error generating PDF with WeasyPrint: {e}")
        flash('Error generating PDF. Check logs.', 'danger')
        return redirect(url_for('users.user_detail', id=id))

    # 3. Definir nombres de archivo
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
    original_filename = f"Inventory_{user.name.replace(' ', '_')}_{timestamp}.pdf"
    secure_filename_to_save = f"{uuid.uuid4().hex}.pdf"
    
    # 4. Guardar el archivo físico
    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename_to_save)
    
    try:
        with open(save_path, 'wb') as f:
            f.write(pdf_bytes)
    except OSError as e:
        current_app.logger.error(f"Error saving PDF file: {e}")
        flash('Error saving inventory file.', 'danger')
        return redirect(url_for('users.user_detail', id=id))

    # 5. Crear el registro 'Attachment' en la BD
    attachment = Attachment(
        filename=original_filename,
        secure_filename=secure_filename_to_save,
        linkable_type='User',
        linkable_id=user.id
    )
    
    db.session.add(attachment)
    db.session.commit()
    
    flash('Inventory snapshot generated and saved.', 'success')
    return redirect(url_for('users.user_detail', id=id))

@users_bp.route('/<int:id>/generate-token', methods=['POST'])
@login_required
@requires_permission('administration', access_level='WRITE')
def generate_token(id):
    """Generates a new API token for the user."""
    user = User.query.get_or_404(id)
    user.generate_token()
    db.session.commit()
    
    # Log the action
    current_app.logger.info(
        f"API Token generated for user {user.email}",
        extra={
            "event.action": "user.token_generated",
            "user.id": user.id,
            "user.email": user.email,
            "source.ip": request.remote_addr
        }
    )
    
    flash('New API Token generated successfully.', 'success')
    return redirect(url_for('users.user_detail', id=id))

@users_bp.route('/org-chart/snapshot', methods=['POST'])
@login_required
@requires_permission('administration', access_level='WRITE')
def create_org_snapshot():
    if request.method == 'POST':
        name = request.form.get('name') or f'Org Chart - {datetime.utcnow().strftime("%Y-%m-%d")}'
        notes = request.form.get('notes')
        
        # 1. Build hierarchy (filter out hidden users)
        users = User.query.filter_by(is_archived=False, hide_from_org_chart=False).all()
        
        data_list = []
        for u in users:
            data_list.append({
                'id': u.id,
                'name': u.name,
                'title': u.job_title,
                'manager_id': u.manager_id,
                'department': u.department,
                'email': u.email
            })
        
        # 2. Save to DB
        snapshot = OrgChartSnapshot(
            name=name,
            chart_data=data_list,
            created_by_id=1, # FIXME: session.get('user_id') but ensuring it's an int
            notes=notes
        )
        # Handle user_id from session safely
        if 'user_id' in from_flask_session_proxy():
             snapshot.created_by_id = from_flask_session_proxy()['user_id']

        db.session.add(snapshot)
        db.session.commit()
        
        flash('Organizational structure snapshot saved successfully.', 'success')
        return redirect(url_for('users.list_org_snapshots'))
    return redirect(url_for('users.org_chart'))

def from_flask_session_proxy():
    from flask import session
    return session

@users_bp.route('/org-chart/snapshots')
@login_required
@requires_permission('administration', access_level='READ_ONLY')
def list_org_snapshots():
    snapshots = OrgChartSnapshot.query.order_by(OrgChartSnapshot.created_at.desc()).all()
    return render_template('users/org_snapshots_list.html', snapshots=snapshots)

@users_bp.route('/org-chart/snapshots/<int:id>')
@login_required
@requires_permission('administration', access_level='READ_ONLY')
def view_org_snapshot(id):
    snapshot = OrgChartSnapshot.query.get_or_404(id)
    return render_template('users/org_snapshot_detail.html', snapshot=snapshot)