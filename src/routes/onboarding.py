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
        item_type = request.form.get('item_type') # 'Software', 'Hardware', 'Task'
        description = request.form.get('description')
        software_id = request.form.get('software_id') or None
        
        # Si es software, hacemos la descripción más bonita automáticamente
        if item_type == 'Software' and software_id:
            soft = Software.query.get(software_id)
            if not description:
                description = f"Provisionar acceso a: {soft.name}"
        
        item = PackItem(pack_id=pack.id, item_type=item_type, description=description, software_id=software_id)
        db.session.add(item)
        db.session.commit()
        flash('Item añadido al pack.')
        return redirect(url_for('onboarding.pack_detail', id=id))

    software_list = Software.query.order_by(Software.name).all()
    return render_template('onboarding/pack_detail.html', pack=pack, software_list=software_list)

# ==========================================
# PROCESO DE ONBOARDING (ENTRADA)
# ==========================================

@onboarding_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_onboarding():
    if request.method == 'POST':
        new_hire_name = request.form['new_hire_name']
        pack_id = request.form.get('pack_id')
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        
        manager_id = request.form.get('manager_id')
        buddy_id = request.form.get('buddy_id')

        # 1. Crear Proceso
        process = OnboardingProcess(
            new_hire_name=new_hire_name,
            pack_id=pack_id,
            start_date=start_date,
            assigned_manager_id=int(manager_id) if manager_id else None,
            assigned_buddy_id=int(buddy_id) if buddy_id else None
        )
        db.session.add(process)
        db.session.commit()
        
        # 2. Generar Checklist: Tareas Globales
        global_tasks = ProcessTemplate.query.filter_by(process_type='onboarding', is_active=True).all()
        for task in global_tasks:
            db.session.add(ProcessItem(
                onboarding_process_id=process.id,
                description=task.name,
                item_type='StaticTask'
            ))
            
        # 3. Generar Checklist: Items del Pack
        if pack_id:
            pack = OnboardingPack.query.get(pack_id)
            for p_item in pack.items:
                db.session.add(ProcessItem(
                    onboarding_process_id=process.id,
                    description=p_item.description,
                    item_type='PackItem',
                    linked_object_id=p_item.software_id if p_item.item_type == 'Software' else None
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
        services = BusinessService.query.filter_by(owner_id=target_user.id).all()
        for s in services:
            db.session.add(ProcessItem(
                offboarding_process_id=process.id,
                description=f"⚠️ TRANSFER SERVICE: {s.name} (User is Owner)",
                item_type='Service',
                linked_object_id=s.id
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
    item.is_completed = not item.is_completed
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

# ==========================================
#  TEMPLATES
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