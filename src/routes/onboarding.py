from src.routes.admin import admin_required
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from ..extensions import db
from ..models import User, Peripheral, License, Software
from ..models import Subscription, PaymentMethod, Risk, BusinessService
# Importamos los modelos nuevos (asegúrate de haberlos registrado en __init__.py primero)
from ..models.onboarding import (
    OnboardingProcess, OffboardingProcess, ProcessItem, 
    OnboardingPack, PackItem, ProcessTemplate
)
from ..utils.helpers import generate_secure_password
from .main import login_required

onboarding_bp = Blueprint('onboarding', __name__)

# --- DASHBOARD PRINCIPAL ---

@onboarding_bp.route('/')
@login_required
def index():
    """Panel principal de HR Processes."""
    active_onboardings = OnboardingProcess.query.filter(OnboardingProcess.status != 'Completed').all()
    active_offboardings = OffboardingProcess.query.filter(OffboardingProcess.status != 'Completed').all()
    packs = OnboardingPack.query.filter_by(is_active=True).all()
    
    return render_template('onboarding/dashboard.html', 
                           onboardings=active_onboardings,
                           offboardings=active_offboardings,
                           packs=packs)

# ==========================================
# GESTIÓN DE PACKS (ONBOARDING)
# ==========================================

@onboarding_bp.route('/packs/new', methods=['POST'])
@login_required
@admin_required
def new_pack():
    name = request.form.get('name')
    if name:
        pack = OnboardingPack(name=name, description=request.form.get('description'))
        db.session.add(pack)
        db.session.commit()
        flash(f'Pack "{name}" creado.')
    return redirect(url_for('onboarding.index'))

@onboarding_bp.route('/packs')
@login_required
def list_packs():
    """Vista dedicada para gestionar packs."""
    packs = OnboardingPack.query.filter_by(is_active=True).all()
    return render_template('onboarding/packs_list.html', packs=packs)

@onboarding_bp.route('/packs/<int:id>', methods=['GET', 'POST'])
@login_required
def pack_detail(id):
    pack = OnboardingPack.query.get_or_404(id)
    
    # Añadir item al pack
    if request.method == 'POST':
        item_type = request.form.get('item_type') # 'Software', 'Hardware', 'Task', 'ServiceAccess'
        description = request.form.get('description')
        software_id = request.form.get('software_id') or None
        subscription_id = request.form.get('subscription_id') or None
        
        # Si es software, hacemos la descripción más bonita automáticamente
        if item_type == 'Software' and software_id:
            soft = Software.query.get(software_id)
            if not description:
                description = f"Provisionar acceso a: {soft.name}"
        elif item_type == 'ServiceAccess' and service_id:
            srv = BusinessService.query.get(service_id)
            if not description:
                description = f"Grant user access to {srv.category}: {srv.name}"
        elif item_type == 'Subscription' and subscription_id:
            sub = Subscription.query.get(subscription_id)
            if not description:
                description = f"Assign user to subscription: {sub.name}"
        
        item = PackItem(
            pack_id=pack.id, 
            item_type=item_type, 
            description=description, 
            software_id=software_id,
            service_id=service_id,
            subscription_id=subscription_id
        )
        db.session.add(item)
        db.session.commit()
        flash('Item añadido al pack.')
        return redirect(url_for('onboarding.pack_detail', id=id))

    all_software = Software.query.order_by(Software.name).all()
    all_services = BusinessService.query.order_by(BusinessService.name).all()
    all_subscriptions = Subscription.query.filter_by(is_archived=False).order_by(Subscription.name).all()
    return render_template('onboarding/pack_detail.html', pack=pack, all_software=all_software, all_services=all_services, all_subscriptions=all_subscriptions)

# ==========================================
# PROCESO DE ONBOARDING (ENTRADA)
# ==========================================

@onboarding_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_onboarding():
    if request.method == 'POST':
        new_hire_name = request.form['new_hire_name']
        target_email = request.form.get('target_email')
        pack_id = request.form.get('pack_id')
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        
        manager_id = request.form.get('manager_id')
        buddy_id = request.form.get('buddy_id')

        # 1. Crear Proceso
        process = OnboardingProcess(
            new_hire_name=new_hire_name,
            target_email=target_email,
            pack_id=pack_id,
            start_date=start_date,
            assigned_manager_id=int(manager_id) if manager_id else None,
            assigned_buddy_id=int(buddy_id) if buddy_id else None
        )
        db.session.add(process)
        db.session.commit()
        
        
        # 0. Generar Checklist: Crear Usuario (SIEMPRE PRIMERO)
        db.session.add(ProcessItem(
            onboarding_process_id=process.id,
            description="👤 Create user account (Automated)",
            item_type='CreateUser'
        ))

        # 2. Generar Checklist: Tareas Globales
        global_tasks = ProcessTemplate.query.filter_by(process_type='onboarding', is_active=True).all()
        for task in global_tasks:
            db.session.add(ProcessItem(
                onboarding_process_id=process.id,
                description=task.name,
                item_type='StaticTask'
            ))
            
        # 3. Generar Checklist: Items del Pack & Provisioning
        if pack_id:
            pack = OnboardingPack.query.get(pack_id)
            for p_item in pack.items:
                # Handle Service Access Provisioning
                linked_obj_id = None
                if p_item.item_type == 'ServiceAccess' and p_item.service_id:
                    linked_obj_id = p_item.service_id
                    # Note: We cannot assign to service.users here because the User record 
                    # for the new hire likely does not exist yet. 
                    # The checklist item "Provision account..." serves as the action trigger.
                elif p_item.item_type == 'Software' and p_item.software_id:
                    linked_obj_id = p_item.software_id
                elif p_item.item_type == 'Subscription' and p_item.subscription_id:
                    linked_obj_id = p_item.subscription_id

                db.session.add(ProcessItem(
                    onboarding_process_id=process.id,
                    description=p_item.description,
                    item_type=p_item.item_type,
                    linked_object_id=linked_obj_id
                ))

        # 4. Social logic (Updated)
        if process.assigned_manager_id:
            manager = User.query.get(process.assigned_manager_id)
            if manager:
                db.session.add(ProcessItem(
                    onboarding_process_id=process.id,
                    description=f"📅 Schedule 1:1 meeting with {manager.name} (Manager)",
                    item_type='SocialTask',
                    linked_object_id=manager.id
                ))

        if process.assigned_buddy_id:
            buddy = User.query.get(process.assigned_buddy_id)
            if buddy:
                db.session.add(ProcessItem(
                    onboarding_process_id=process.id,
                    description=f"☕ Schedule welcome coffee with buddy: {buddy.name}",
                    item_type='SocialTask',
                    linked_object_id=buddy.id
                ))
        
        db.session.commit()
        
        # POST-COMMIT: Handle automatic user assignment for ServiceAccess
        # We need the User object. But wait, OnboardingProcess doesn't necessarily have a User yet (new_hire_name).
        # This app creates the user separately or later?
        # The prompt says "Añadir al empleado a la lista service.users".
        # If the employee doesn't exist as a User yet, we can't add them.
        # Let's check the new_onboarding flow. It takes `new_hire_name`. `user_id` is nullable.
        # So we probably can only generate the Task to provision. 
        # BUT the requirement says: "Añadir al empleado a la lista service.users".
        # Maybe we should only do this if the user is already selected/created?
        # Re-reading: "Al aplicar un Pack, si el item es ServiceAccess: Añadir al empleado a la lista service.users."
        # This implies we have a user. If we only have `new_hire_name`, we can't.
        # However, looking at `form_onboarding.html` (assumed), maybe we can select an existing one?
        # The form has `users` passed to it.
        # If we are onboarding a NEW hire, usually they don't have a user yet.
        # Maybe I should create the checklist item, and the automatic assignment happens when the user is eventually created/linked?
        # OR, maybe the request implies we create the User here? No, 'new_hire_name' suggests text only.
        
        # Let's assume for now we just create the checklist item, and if we CAN link them (e.g. if we add a user creation step later), we do.
        # Only if `user_id` is somehow provided (it's not in the form input `new_hire_name`).
        
        # Wait, step 3 says: "Añadir al empleado a la lista service.users".
        # If `new_onboarding` doesn't create a `User`, then I can't do M2M.
        # I'll stick to creating the checklist item for now, and maybe add a comment/TODO about the M2M.
        # Logic:
        # * Generar item en el checklist: "Provision account in {service.name}".
        
        flash(f'Onboarding started for {new_hire_name}.')
        return redirect(url_for('onboarding.onboarding_detail', id=process.id))

    packs = OnboardingPack.query.filter_by(is_active=True).all()
    users = User.query.filter_by(is_archived=False).all() # Para asignar usuario si ya existe
    return render_template('onboarding/form_onboarding.html', packs=packs, users=users)

@onboarding_bp.route('/view/<int:id>')
@login_required
def onboarding_detail(id):
    process = OnboardingProcess.query.get_or_404(id)
    return render_template('onboarding/process_detail.html', process=process, type='onboarding')

# ==========================================
# PROCESO DE OFFBOARDING (SALIDA)
# ==========================================

@onboarding_bp.route('/offboarding/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_offboarding():
    if request.method == 'POST':
        user_id = request.form['user_id']
        departure_date = datetime.strptime(request.form['departure_date'], '%Y-%m-%d').date()
        target_user = User.query.get_or_404(user_id)
        
        manager_id = session.get('user_id') 

        process = OffboardingProcess(
            user_id=user_id,
            manager_id=manager_id,
            departure_date=departure_date
        )
        db.session.add(process)
        db.session.commit()
        
        # 1. HARDWARE
        for assignment in target_user.assignments:
            if not assignment.checked_in_date:
                db.session.add(ProcessItem(
                    offboarding_process_id=process.id,
                    description=f"💻 Pick up Asset: {assignment.asset.name} ({assignment.asset.serial_number})",
                    item_type='Asset',
                    linked_object_id=assignment.asset.id
                ))

        peripherals = Peripheral.query.filter_by(user_id=target_user.id).all()
        for p in peripherals:
            db.session.add(ProcessItem(
                offboarding_process_id=process.id,
                description=f"⌨️ Pick up Peripheral: {p.name}",
                item_type='Peripheral',
                linked_object_id=p.id
            ))
            
        # 2. SOFTWARE
        licenses = License.query.filter_by(user_id=target_user.id).all()
        for l in licenses:
            desc = f"🔑 Revoke License: {l.name}"
            if l.software:
                desc += f" ({l.software.name})"
            db.session.add(ProcessItem(
                offboarding_process_id=process.id,
                description=desc,
                item_type='License',
                linked_object_id=l.id
            ))
            
        subscriptions = Subscription.query.filter_by(user_id=target_user.id).all()
        for sub in subscriptions:
            db.session.add(ProcessItem(
                offboarding_process_id=process.id,
                description=f"🔄 Cancel/Transfer Subscription: {sub.name}",
                item_type='Subscription'
            ))

        # 2b. Subscription Access (Revoke)
        subscriptions_access = Subscription.query.filter(Subscription.users.contains(target_user)).all()
        for sub in subscriptions_access:
             db.session.add(ProcessItem(
                offboarding_process_id=process.id,
                description=f"🛑 Revoke access to Subscription: {sub.name}",
                item_type='RevokeSubscriptionAccess',
                linked_object_id=sub.id
            ))

        # 3. COMPLIANCE & OWNERSHIP
        payment_methods = PaymentMethod.query.filter_by(user_id=target_user.id).all()
        for pm in payment_methods:
            linked_subs = len(pm.subscriptions)
            desc = f"⚠️ BLOCKING: Card '{pm.name}' has {linked_subs} subscriptions. Change before canceling." if linked_subs > 0 else f"💳 Recover/Cancel Payment Method: {pm.name}"
            db.session.add(ProcessItem(
                offboarding_process_id=process.id,
                description=desc,
                item_type='PaymentMethod',
                linked_object_id=pm.id
            ))

        # CORRECCIÓN RIESGOS: Usamos 'risk_description' que es el campo real en tu modelo
        risks = Risk.query.filter_by(owner_id=target_user.id).all()
        for r in risks:
            # Acortamos la descripción si es muy larga para que quepa en el checklist
            short_desc = (r.risk_description[:75] + '..') if len(r.risk_description) > 75 else r.risk_description
            db.session.add(ProcessItem(
                offboarding_process_id=process.id,
                description=f"⚠️ TRANSFER RISK: {short_desc}",
                item_type='Risk',
                linked_object_id=r.id
            ))

        # CORRECCIÓN SERVICIOS: Usamos 'BusinessService'
        # 1. Transfer Ownership of Services owned by user
        services_owned = BusinessService.query.filter_by(owner_id=target_user.id).all()
        for s in services_owned:
            db.session.add(ProcessItem(
                offboarding_process_id=process.id,
                description=f"⚠️ TRANSFER SERVICE: {s.name} (User is Owner)",
                item_type='ServiceOwnership',
                linked_object_id=s.id
            ))
            
        # 2. Revoke Access to Services/Applications
        # Find all services where the user is in the 'users' list
        services_access = BusinessService.query.filter(BusinessService.users.contains(target_user)).all()
        for s in services_access:
            cat_label = s.category if s.category else 'Service'
            db.session.add(ProcessItem(
                offboarding_process_id=process.id,
                description=f"🛑 Revoke access to {cat_label}: {s.name}",
                item_type='RevokeAccess',
                linked_object_id=s.id
            ))

        # 3. CREDENTIALS
        # Import Credential model
        from ..models.credentials import Credential
        credentials_owned = Credential.query.filter_by(owner_id=target_user.id, owner_type='User').all()
        for cred in credentials_owned:
            db.session.add(ProcessItem(
                offboarding_process_id=process.id,
                description=f"🔑 REASSIGN CREDENTIAL: {cred.name} ({cred.type})",
                item_type='Credential',
                linked_object_id=cred.id
            ))

        # 4. TAREAS GLOBALES
        static_tasks = ProcessTemplate.query.filter_by(process_type='offboarding', is_active=True).all()
        for task in static_tasks:
            db.session.add(ProcessItem(
                offboarding_process_id=process.id,
                description=task.name,
                item_type='StaticTask'
            ))

        db.session.commit()
        flash(f'Offboarding started for {target_user.name}. Checklist created.', 'warning')
        return redirect(url_for('onboarding.offboarding_detail', id=process.id))

    users = User.query.filter_by(is_archived=False).order_by(User.name).all()
    return render_template('onboarding/form_offboarding.html', users=users)

@onboarding_bp.route('/offboarding/view/<int:id>')
@login_required
def offboarding_detail(id):
    process = OffboardingProcess.query.get_or_404(id)
    users = User.query.filter_by(is_archived=False).order_by(User.name).all()
    
    # Pre-fetch payment methods for the template
    pm_ids = [item.linked_object_id for item in process.items if item.item_type == 'PaymentMethod' and item.linked_object_id]
    payment_methods = {}
    if pm_ids:
        pms = PaymentMethod.query.filter(PaymentMethod.id.in_(pm_ids)).all()
        payment_methods = {pm.id: pm for pm in pms}
        
    return render_template('onboarding/process_detail.html', process=process, type='offboarding', users=users, payment_methods=payment_methods)

# ==========================================
# ACCIONES COMUNES (CHECKLIST)
# ==========================================

@onboarding_bp.route('/item/<int:id>/toggle', methods=['POST'])
@login_required
def toggle_item(id):
    item = ProcessItem.query.get_or_404(id)
    target_state = not item.is_completed
    item.is_completed = target_state

    # Automation: If ServiceAccess item completed, link user to service
    if target_state and item.item_type == 'ServiceAccess' and item.linked_object_id and item.onboarding_process_id:
        process = item.onboarding_process
        if process and process.user: # Requires User to be created/linked first
            service = BusinessService.query.get(item.linked_object_id)
            if service:
                if process.user not in service.users:
                    service.users.append(process.user)
                    flash(f'User automatically added to service access list: {service.name}', 'success')
                else:
                    flash(f'User already has access to {service.name}.', 'info')

    db.session.commit()
    
    # Redirigir inteligentemente
    if item.onboarding_process_id:
        return redirect(url_for('onboarding.onboarding_detail', id=item.onboarding_process_id))
    elif item.offboarding_process_id:
        return redirect(url_for('onboarding.offboarding_detail', id=item.offboarding_process_id))
    
    return redirect(url_for('onboarding.index'))

@onboarding_bp.route('/process/<string:type>/<int:id>/complete', methods=['POST'])
@login_required
@admin_required
def complete_process(type, id):
    """Marca el proceso entero como completado y archiva usuario si es offboarding."""
    if type == 'onboarding':
        process = OnboardingProcess.query.get_or_404(id)
        process.status = 'Completed'
        flash(f'Onboarding de {process.new_hire_name} completado.', 'success')
        
    else: # Offboarding
        process = OffboardingProcess.query.get_or_404(id)
        process.status = 'Completed'
        process.departure_date = datetime.utcnow().date() # Fijar fecha real de cierre
        
        # LÓGICA DE ARCHIVADO AUTOMÁTICO
        if process.user:
            process.user.is_archived = True
            # Opcional: Limpiar su password o tokens de sesión aquí si tuvieras
        flash(f'Offboarding completado. El usuario {process.user.name} ha sido archivado.', 'warning')
        
    db.session.commit()
    return redirect(url_for('onboarding.index'))

@onboarding_bp.route('/offboarding/<int:process_id>/revoke_service/<int:item_id>', methods=['POST'])
@login_required
@admin_required
def revoke_service_access(process_id, item_id):
    process = OffboardingProcess.query.get_or_404(process_id)
    item = ProcessItem.query.get_or_404(item_id)
    
    # Validation
    # Let's check the model. ProcessItem has separate FKs or a single one?
    # Based on new_onboarding/offboarding codes:
    # db.session.add(ProcessItem(offboarding_process_id=process.id ...
    # So check offboarding_process_id
    if item.offboarding_process_id != process.id:
        flash('Invalid item for this process.', 'danger')
        return redirect(url_for('onboarding.onboarding_detail', id=process.id))

    if item.item_type != 'RevokeAccess':
        flash('Invalid item type.', 'danger')
        return redirect(url_for('onboarding.onboarding_detail', id=process.id))

    service = BusinessService.query.get(item.linked_object_id)
    target_user = process.user
    
    if service and target_user:
        if target_user in service.users:
            service.users.remove(target_user)
            flash(f'User removed from {service.name}.', 'success')
        else:
            flash(f'User was not in {service.name} (already removed?).', 'warning')
            
        # Mark item as completed
        item.is_completed = True
        item.completed_at = datetime.utcnow()
        db.session.commit()
    else:
        flash('Service or User not found.', 'danger')

    return redirect(url_for('onboarding.onboarding_detail', id=process.id))

@onboarding_bp.route('/offboarding/<int:process_id>/revoke_subscription/<int:item_id>', methods=['POST'])
@login_required
@admin_required
def revoke_subscription_access(process_id, item_id):
    process = OffboardingProcess.query.get_or_404(process_id)
    item = ProcessItem.query.get_or_404(item_id)
    
    if item.offboarding_process_id != process.id:
        flash('Invalid item for this process.', 'danger')
        return redirect(url_for('onboarding.offboarding_detail', id=process.id))

    if item.item_type != 'RevokeSubscriptionAccess':
        flash('Invalid item type.', 'danger')
        return redirect(url_for('onboarding.offboarding_detail', id=process.id))

    subscription = Subscription.query.get(item.linked_object_id)
    target_user = process.user
    
    if subscription and target_user:
        if target_user in subscription.users:
            subscription.users.remove(target_user)
            flash(f'User removed from {subscription.name}.', 'success')
        else:
            flash(f'User was not in {subscription.name} (already removed?).', 'warning')
            
        item.is_completed = True
        item.completed_at = datetime.utcnow()
        db.session.commit()
    else:
        flash('Subscription or User not found.', 'danger')

    return redirect(url_for('onboarding.offboarding_detail', id=process.id))

@onboarding_bp.route('/process/<int:process_id>/create_user/<int:item_id>', methods=['POST'])
@login_required
@admin_required
def create_user_account(process_id, item_id):
    process = OnboardingProcess.query.get_or_404(process_id)
    item = ProcessItem.query.get_or_404(item_id)
    
    # Validation
    if item.onboarding_process_id != process.id:
        flash('Invalid item for this process.', 'danger')
        return redirect(url_for('onboarding.onboarding_detail', id=process.id))

    if item.item_type != 'CreateUser':
        flash('Invalid item type.', 'danger')
        return redirect(url_for('onboarding.onboarding_detail', id=process.id))
        
    # Check if user already linked
    if process.user_id:
        flash('Process already has a user linked.', 'warning')
        return redirect(url_for('onboarding.onboarding_detail', id=process.id))

    # Generate Email
    # Generate Email
    # Format: firstname.lastname@example.com (simplified logic)
    if process.target_email:
        email = process.target_email
    else:
        # Removing special chars, spaces to dots
        clean_name = "".join(c for c in process.new_hire_name if c.isalnum() or c.isspace()).lower()
        email_local = clean_name.replace(" ", ".")
        email = f"{email_local}@example.com"
    
    # Generate Password
    password = generate_secure_password()
    
    # Check if email exists
    if User.query.filter_by(email=email).first():
        # Fallback: append random number
        import random
        email = f"{email_local}{random.randint(10,99)}@example.com"
    
    # Create User
    new_user = User(name=process.new_hire_name, email=email, role='user')
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.flush() # Get ID
    
    # Link to Process
    process.user_id = new_user.id
    
    # Mark item complete
    item.is_completed = True
    
    db.session.commit()
    
    flash(f"User created!\nEmail: {email}\nPassword: {password}", "success")
    return redirect(url_for('onboarding.onboarding_detail', id=process.id))

@onboarding_bp.route('/process/<int:process_id>/add_to_service/<int:item_id>', methods=['POST'])
@login_required
@admin_required
def add_user_to_service(process_id, item_id):
    process = OnboardingProcess.query.get_or_404(process_id)
    item = ProcessItem.query.get_or_404(item_id)
    
    if item.item_type != 'ServiceAccess' or not item.linked_object_id:
        flash('Invalid item type.', 'danger')
        return redirect(url_for('onboarding.onboarding_detail', id=process.id))

    service = BusinessService.query.get(item.linked_object_id)
    if not service:
        flash('Service not found.', 'danger')
        return redirect(url_for('onboarding.onboarding_detail', id=process.id))
        
    if not process.user:
        flash('No user linked to this onboarding process yet. Create the user first.', 'warning')
        return redirect(url_for('onboarding.onboarding_detail', id=process.id))
        
    if process.user not in service.users:
        service.users.append(process.user)
        # Avoid double flash if toggle also triggers? No, toggle triggers on is_completed change.
        # This button is manual. It also marks completed.
        flash(f'User {process.user.name} added to {service.name}.', 'success')
        item.is_completed = True
        db.session.commit()
    else:
        flash(f'User already in {service.name}.', 'info')
        item.is_completed = True
        db.session.commit()
        
    return redirect(url_for('onboarding.onboarding_detail', id=process.id))

@onboarding_bp.route('/process/<int:process_id>/add_to_subscription/<int:item_id>', methods=['POST'])
@login_required
@admin_required
def add_user_to_subscription(process_id, item_id):
    process = OnboardingProcess.query.get_or_404(process_id)
    item = ProcessItem.query.get_or_404(item_id)
    
    if item.item_type != 'Subscription' or not item.linked_object_id:
        flash('Invalid item type.', 'danger')
        return redirect(url_for('onboarding.onboarding_detail', id=process.id))

    subscription = Subscription.query.get(item.linked_object_id)
    if not subscription:
        flash('Subscription not found.', 'danger')
        return redirect(url_for('onboarding.onboarding_detail', id=process.id))
        
    if not process.user:
        flash('No user linked to this onboarding process yet. Create the user first.', 'warning')
        return redirect(url_for('onboarding.onboarding_detail', id=process.id))
        
    if process.user not in subscription.users:
        subscription.users.append(process.user)
        flash(f'User {process.user.name} added to subscription {subscription.name}.', 'success')
        item.is_completed = True
        db.session.commit()
    else:
        flash(f'User already has access to {subscription.name}.', 'info')
        item.is_completed = True
        db.session.commit()
        
    return redirect(url_for('onboarding.onboarding_detail', id=process.id))

# ==========================================
# API / UTILS
# ==========================================

@onboarding_bp.route('/templates')
@login_required
def list_templates():
    tasks = ProcessTemplate.query.all()
    return render_template('onboarding/templates_list.html', tasks=tasks)

@onboarding_bp.route('/templates/new', methods=['POST'])
@login_required
@admin_required
def new_template_task():
    name = request.form.get('name')
    process_type = request.form.get('process_type')
    if name and process_type:
        t = ProcessTemplate(name=name, process_type=process_type)
        db.session.add(t)
        db.session.commit()
        flash('Tarea global creada.')
    return redirect(url_for('onboarding.list_templates'))

@onboarding_bp.route('/templates/<int:id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_template_task(id):
    t = ProcessTemplate.query.get_or_404(id)
    t.is_active = not t.is_active
    db.session.commit()
    flash('Estado de tarea actualizado.')
    return redirect(url_for('onboarding.list_templates'))

# ==========================================
#  ARCHIVED PROCESSES
# ==========================================

# Histórico de Procesos (Auditoría)
@onboarding_bp.route('/history')
@login_required
def history():
    """Muestra los procesos completados para auditoría."""
    completed_onboardings = OnboardingProcess.query.filter_by(status='Completed').order_by(OnboardingProcess.id.desc()).all()
    completed_offboardings = OffboardingProcess.query.filter_by(status='Completed').order_by(OffboardingProcess.id.desc()).all()
    
    return render_template('onboarding/history.html', 
                           onboardings=completed_onboardings,
                           offboardings=completed_offboardings)

# ==========================================
#  OFFBOARDING TRANSFERS
# ==========================================

@onboarding_bp.route('/transfer/risk/<int:id>', methods=['POST'])
@login_required
@admin_required
def transfer_risk(id):
    risk = Risk.query.get_or_404(id)
    new_owner_id = request.form.get('new_owner_id')
    redirect_url = request.form.get('redirect_url')
    
    # Update owner (None if empty, meaning unassigned)
    risk.owner_id = int(new_owner_id) if new_owner_id else None
    
    # Auto-complete related offboarding item if exists
    offboarding_item = ProcessItem.query.filter_by(
        item_type='Risk', 
        linked_object_id=id, 
        is_completed=False
    ).first()
    if offboarding_item and offboarding_item.offboarding_process_id:
        offboarding_item.is_completed = True
        
    db.session.commit()
    
    if risk.owner:
        flash(f'Risk "{risk.risk_description[:30]}..." transferred to {risk.owner.name}.', 'success')
    else:
        flash(f'Risk "{risk.risk_description[:30]}..." is now unassigned.', 'info')
        
    return redirect(redirect_url or request.referrer)

@onboarding_bp.route('/transfer/service/<int:id>', methods=['POST'])
@login_required
@admin_required
def transfer_service(id):
    service = BusinessService.query.get_or_404(id)
    new_owner_id = request.form.get('new_owner_id')
    redirect_url = request.form.get('redirect_url')
    
    # Update owner
    service.owner_id = int(new_owner_id) if new_owner_id else None
    
    # Auto-complete related offboarding item if exists
    offboarding_item = ProcessItem.query.filter_by(
        item_type='Service', 
        linked_object_id=id, 
        is_completed=False
    ).first()
    if offboarding_item and offboarding_item.offboarding_process_id:
        offboarding_item.is_completed = True
        
    db.session.commit()
    
    if service.owner:
        flash(f'Service "{service.name}" transferred to {service.owner.name}.', 'success')
    else:
        flash(f'Service "{service.name}" is now unassigned.', 'info')
        
    return redirect(redirect_url or request.referrer)

@onboarding_bp.route('/transfer/credential/<int:id>', methods=['POST'])
@login_required
@admin_required
def transfer_credential(id):
    from ..models.credentials import Credential
    
    credential = Credential.query.get_or_404(id)
    new_owner_id = request.form.get('new_owner_id')
    redirect_url = request.form.get('redirect_url')
    
    # Update owner
    if new_owner_id:
        credential.owner_id = int(new_owner_id)
        credential.owner_type = 'User'  # Ensure it's set to User
    else:
        credential.owner_id = None
    
    # Auto-complete related offboarding item if exists
    offboarding_item = ProcessItem.query.filter_by(
        item_type='Credential', 
        linked_object_id=id, 
        is_completed=False
    ).first()
    if offboarding_item and offboarding_item.offboarding_process_id:
        offboarding_item.is_completed = True
        
    db.session.commit()
    
    if credential.owner:
        flash(f'Credential "{credential.name}" transferred to {credential.owner.name}.', 'success')
    else:
        flash(f'Credential "{credential.name}" is now unassigned.', 'info')
        
    return redirect(redirect_url or request.referrer)